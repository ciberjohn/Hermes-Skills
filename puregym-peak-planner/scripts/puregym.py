#!/usr/bin/env python3
"""PureGym peak planner — sample live attendance, then find the quiet hours.

The PureGym member API exposes live attendance only; there is no history or
forecast endpoint. So this tool samples the live headcount on a schedule, keeps
a local SQLite history, and blends what it has measured with a published-pattern
prior so an answer is useful from day one and becomes honest as data arrives.

Every estimate carries a confidence label: measured, emerging, early or modelled.

Usage:
  puregym.py doctor                        # check config, credentials and API
  puregym.py sample                        # one live reading -> sqlite
  puregym.py advise [--day today|tomorrow|mon] [--top 3] [--all-hours]
  puregym.py report [--day today|tomorrow] [--all-hours]
  puregym.py visits [--top 10]             # the member's own recent visits
  puregym.py stats

Configuration comes from the environment, optionally seeded by a KEY=VALUE file
at $PUREGYM_CONFIG (default ~/.config/puregym/config.env, mode 0600):

  PUREGYM_EMAIL              member email (required)
  PUREGYM_PIN                the PIN itself — prefer a secret backend instead
  PUREGYM_PIN_FILE           file containing only the PIN
  PUREGYM_SECRET_CMD         command whose stdout is the PIN (any vault CLI)
  SECRET_BACKEND=infisical   use the built-in Infisical reader instead
  PUREGYM_DATA_DIR           where the sqlite + token live
                             (default ~/.local/share/puregym)
  PUREGYM_GYM_ID             pin a gym id; otherwise the home gym is detected

Nothing secret is ever printed: logs get counts and timestamps only.
"""
from __future__ import annotations

import json
import os
import shlex
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Anything this process creates (database, log, token cache) is private by default.
os.umask(0o077)

# ---------------------------------------------------------------- configuration
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _warn_if_exposed(path: str) -> None:
    """Warn (never fail) when a secrets file is readable by group or others."""
    try:
        mode = os.stat(os.path.expanduser(path)).st_mode & 0o777
    except OSError:
        return
    if mode & 0o077:
        print(
            f"WARN: {path} is mode {mode:03o} — chmod 600 it; it can hold a credential",
            file=sys.stderr,
        )


def _default_config_path() -> str:
    """First existing config wins: $XDG_CONFIG_HOME, ~/.config, then the skill dir.

    The skill-directory option matters for agent runtimes that redirect $HOME
    (Hermes profiles do), where ~ is not the human's home directory.
    """
    candidates: list[str] = []
    if os.environ.get("XDG_CONFIG_HOME"):
        candidates.append(
            os.path.join(os.environ["XDG_CONFIG_HOME"], "puregym", "config.env")
        )
    candidates.append(os.path.expanduser("~/.config/puregym/config.env"))
    candidates.append(os.path.join(SKILL_DIR, "config.env"))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[-1]


CONFIG_FILE = os.environ.get("PUREGYM_CONFIG") or _default_config_path()


def load_config() -> None:
    """Seed os.environ from a KEY=VALUE file. Real env vars always win."""
    if not os.path.exists(CONFIG_FILE):
        return
    _warn_if_exposed(CONFIG_FILE)
    with open(CONFIG_FILE) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_config()

DATA_DIR = os.environ.get("PUREGYM_DATA_DIR") or os.path.expanduser(
    "~/.local/share/puregym"
)
DB_PATH = os.path.join(DATA_DIR, "puregym.sqlite")
TOKEN_PATH = os.path.join(DATA_DIR, "puregym_token.json")

MEMBER_EMAIL = os.environ.get("PUREGYM_EMAIL", "")
GYM_ID = os.environ.get("PUREGYM_GYM_ID", "").strip()
UA = os.environ.get("PUREGYM_USER_AGENT", "PureGym/1523 CFNetwork/1312 Darwin/21.0.0")
AUTH_URL = "https://auth.puregym.com/connect/token"
CAPI = "https://capi.puregym.com"
LOCAL_TZ = timezone(timedelta(hours=0))  # fallback only; Europe/London preferred

# PureGym's edge resets TLS connections now and then; retry instead of crashing.
SESSION = requests.Session()
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=4, connect=4, read=3, status=3, backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=True,
        ),
        pool_maxsize=4,
    ),
)


# ---------------------------------------------------------------- time helpers
def london_now() -> datetime:
    """Europe/London wall clock without needing tzdata."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        return datetime.now(LOCAL_TZ)


# ---------------------------------------------------------------- credentials
def _read_plain(path: str) -> str:
    """Read a file that holds either a bare value or a single KEY=VALUE line."""
    _warn_if_exposed(path)
    with open(os.path.expanduser(path)) as fh:
        text = fh.read().strip()
    if "\n" not in text and "=" in text:
        key, value = text.split("=", 1)
        if key.strip().isupper():
            return value.strip()
    return text


def _read_infisical_token(path: str) -> str:
    """Read a token from a file that may be bare, or hold KEY=VALUE lines."""
    _warn_if_exposed(path)
    with open(os.path.expanduser(path)) as fh:
        text = fh.read().strip()
    if "=" in text:
        values: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        for name in ("INFISICAL_TOKEN", "TOKEN", "token"):
            if values.get(name):
                return values[name]
        if values:
            return next(iter(values.values()))
    return text.splitlines()[0].strip() if text else ""


def _infisical_pin() -> str:
    """Read the PIN from a self-hosted Infisical over its REST API.

    Requires INFISICAL_URL, INFISICAL_PROJECT_ID and a token in
    INFISICAL_TOKEN or the file named by INFISICAL_TOKEN_FILE.
    """
    base = (os.environ.get("INFISICAL_URL") or "").rstrip("/")
    project = os.environ.get("INFISICAL_PROJECT_ID") or os.environ.get(
        "INFISICAL_PROJECT", ""
    )
    env = os.environ.get("INFISICAL_ENV", "prod")
    key = os.environ.get("INFISICAL_SECRET_KEY", "PureGym")
    secret_path = os.environ.get("INFISICAL_SECRET_PATH", "/")
    token = os.environ.get("INFISICAL_TOKEN", "")
    if not token:
        token_file = os.environ.get(
            "INFISICAL_TOKEN_FILE", os.path.expanduser("~/.infisical-auth")
        )
        token = _read_infisical_token(token_file)
    missing = [n for n, v in (("INFISICAL_URL", base), ("INFISICAL_PROJECT_ID", project),
                              ("INFISICAL_TOKEN", token)) if not v]
    if missing:
        raise RuntimeError("Infisical backend needs " + ", ".join(missing))
    if not token.isascii() or any(c.isspace() for c in token):
        raise RuntimeError("Infisical token contains whitespace or non-ASCII characters")
    try:
        r = SESSION.get(
            f"{base}/api/v3/secrets/raw",
            params={"workspaceId": project, "environment": env, "secretPath": secret_path},
            headers={"Authorization": f"Bearer {token}"},
            timeout=25,
        )
    except requests.RequestException as exc:
        # never surface the request URL: it carries the workspace id
        raise RuntimeError(f"Infisical request failed ({type(exc).__name__})") from None
    if r.status_code != 200:
        raise RuntimeError(f"Infisical returned HTTP {r.status_code}")
    try:
        secrets = r.json().get("secrets", [])
    except ValueError:
        raise RuntimeError("Infisical returned a non-JSON body") from None
    for secret in secrets:
        if secret.get("secretKey") == key:
            return str(secret["secretValue"]).strip()
    raise RuntimeError(f"secret {key} not found in Infisical env {env}")


def secret_backend() -> str:
    """Describe the backend member_pin() will use, in the same order."""
    if os.environ.get("PUREGYM_SECRET_CMD"):
        return "command PUREGYM_SECRET_CMD"
    if (os.environ.get("SECRET_BACKEND") or "").lower() == "infisical":
        return "Infisical REST"
    if os.environ.get("PUREGYM_PIN_FILE"):
        return f"file {os.environ['PUREGYM_PIN_FILE']}"
    if os.environ.get("PUREGYM_PIN"):
        return "env var PUREGYM_PIN"
    return "unconfigured"


def member_pin() -> str:
    """Resolve the member PIN. Most secure backend first; PUREGYM_PIN last."""
    cmd = os.environ.get("PUREGYM_SECRET_CMD")
    if cmd:
        proc = subprocess.run(
            ["sh", "-c", cmd], capture_output=True, text=True, timeout=60
        )
        if proc.returncode != 0:
            # deliberately no stdout/stderr: a vault CLI may echo the secret
            raise RuntimeError(
                f"secret command failed (rc={proc.returncode}); run it by hand to see why"
            )
        lines = proc.stdout.strip().splitlines()
        if lines and lines[0].strip():
            return lines[0].strip()
        raise RuntimeError("secret command produced no output")
    if (os.environ.get("SECRET_BACKEND") or "").lower() == "infisical":
        return _infisical_pin()
    pin_file = os.environ.get("PUREGYM_PIN_FILE")
    if pin_file:
        pin = _read_plain(pin_file).strip()
        if pin:
            return pin
        raise RuntimeError(f"{pin_file} is empty")
    pin = os.environ.get("PUREGYM_PIN")
    if pin:
        return pin
    raise RuntimeError(
        "no credential backend configured — set PUREGYM_SECRET_CMD (any vault CLI), "
        "SECRET_BACKEND=infisical, PUREGYM_PIN_FILE or PUREGYM_PIN; "
        "see references/credentials.md"
    )


# ---------------------------------------------------------------- puregym api
def _load_token() -> str | None:
    try:
        with open(TOKEN_PATH) as fh:
            d = json.load(fh)
        if d.get("expires_at", 0) > time.time() + 3600:
            return d["access_token"]
    except Exception:
        pass
    return None


PERSIST_TOKEN = True  # doctor turns this off so it leaves no trace


def _save_token(tok: str, expires_in: int) -> None:
    if not PERSIST_TOKEN:
        return
    os.makedirs(DATA_DIR, mode=0o700, exist_ok=True)
    fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        # os.open's mode is ignored for an existing file; force it
        os.fchmod(fh.fileno(), 0o600)
        json.dump({"access_token": tok, "expires_at": time.time() + expires_in}, fh)


def access_token(force: bool = False, persist: bool = True) -> str:
    if not force:
        tok = _load_token()
        if tok:
            return tok
    if not MEMBER_EMAIL:
        raise RuntimeError("PUREGYM_EMAIL is not set")
    pin = member_pin()
    r = SESSION.post(
        AUTH_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA},
        data={
            "grant_type": "password",
            "username": MEMBER_EMAIL,
            "password": pin,
            "scope": "pgcapi offline_access",
            "client_id": "ro.client",
        },
        timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    _save_token(d["access_token"], int(d.get("expires_in", 3600)))
    return d["access_token"]


def api_get(path: str, **params: Any) -> Any:
    tok = access_token()
    for attempt in (0, 1):
        r = SESSION.get(
            CAPI + path,
            params=params,
            headers={"Authorization": f"Bearer {tok}", "User-Agent": UA},
            timeout=30,
        )
        if r.status_code == 401 and attempt == 0:
            tok = access_token(force=True)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("unreachable")


def home_gym() -> dict:
    return api_get("/api/v2/member")["HomeGym"]


def selected_gym() -> dict:
    """The gym to sample: PUREGYM_GYM_ID if pinned, else the member's home gym."""
    gym = home_gym()
    if GYM_ID and str(gym.get("Id")) != GYM_ID:
        for candidate in api_get("/api/v2/gyms/"):
            if str(candidate.get("Id")) == GYM_ID:
                return candidate
        raise RuntimeError(f"gym id {GYM_ID} not found in the gym list")
    return gym


def attendance(gym_id: int) -> dict:
    return api_get("/api/v2/gymSessions/gym", gymId=gym_id)


# ---------------------------------------------------------------- storage
SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    ts_local TEXT NOT NULL,
    weekday INTEGER NOT NULL,   -- 0 = Monday
    hour INTEGER NOT NULL,
    people INTEGER NOT NULL,
    classes INTEGER NOT NULL DEFAULT 0,
    UNIQUE(ts_utc)
);
CREATE INDEX IF NOT EXISTS idx_wd_hour ON readings(weekday, hour);
CREATE TABLE IF NOT EXISTS misses (
    ts_utc TEXT PRIMARY KEY,
    note TEXT
);
"""


def db() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def _as_int(value: Any) -> int | None:
    """PureGym sends null for TotalPeopleInGym when the live counter is offline."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stale_note(conn: sqlite3.Connection, now: datetime) -> str | None:
    row = conn.execute("SELECT MAX(ts_utc) m FROM readings").fetchone()
    if not row or not row[0]:
        return None
    last = datetime.fromisoformat(row[0])
    hours = (now.astimezone(timezone.utc) - last.astimezone(timezone.utc)).total_seconds() / 3600
    if hours >= 3:
        return f"WARN: no live reading for {hours:.1f}h — PureGym counter may be down"
    return None


def record_reading(now: datetime, gym_name: str, people: int, classes: int) -> int:
    conn = db()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO readings(ts_utc, ts_local, weekday, hour, people, classes)"
            " VALUES (?,?,?,?,?,?)",
            (
                now.astimezone(timezone.utc).isoformat(timespec="seconds"),
                now.isoformat(timespec="seconds"),
                now.weekday(),
                now.hour,
                people,
                classes,
            ),
        )
    n = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    conn.close()
    return n


def record_miss(now: datetime, note: str) -> None:
    conn = db()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO misses(ts_utc, note) VALUES (?,?)",
            (now.astimezone(timezone.utc).isoformat(timespec="seconds"), note),
        )
    conn.close()


def cmd_sample() -> int:
    now = london_now()
    gym = selected_gym()
    gym_name = gym.get("Name", "PureGym")
    people: int | None = None
    classes = 0
    try:
        # the counter occasionally blips to null for a few seconds; give it 3 tries
        for attempt in range(3):
            a = attendance(gym["Id"])
            people = _as_int(a.get("TotalPeopleInGym"))
            classes = _as_int(a.get("TotalPeopleInClasses")) or 0
            if people is not None:
                break
            if attempt < 2:
                time.sleep(4)
    except requests.RequestException as exc:
        # transient TLS resets / timeouts: a skipped sample is not an incident
        detail = (str(exc).splitlines() or [type(exc).__name__])[0][:150]
        print(f"{now:%Y-%m-%d %H:%M} {gym_name}: network error — {type(exc).__name__}: {detail}")
        conn = db()
        note = _stale_note(conn, now)
        conn.close()
        if note:
            print(note)
        return 0

    if people is None:
        # never write a fake zero — a null would read as "empty gym" and poison the model
        record_miss(now, "counter returned null")
        print(f"{now:%Y-%m-%d %H:%M} {gym_name}: no reading (counter returned null)")
        conn = db()
        note = _stale_note(conn, now)
        conn.close()
        if note:
            print(note)
        return 0

    rows = record_reading(now, gym_name, people, classes)
    print(f"{now:%Y-%m-%d %H:%M} {gym_name}: {people} people, {classes} in classes (rows={rows})")
    return 0


# ---------------------------------------------------------------- prior model
# Relative busyness 0-100 for a typical UK 24h gym, indexed [weekday][hour].
# Derived from PureGym's own published visit patterns for a commuter town
# (Mon/Tue busiest, Sun quietest, weekday peak 17:00-19:30, dead 10:00-15:00
# and after 21:30). Used only as a prior; measured data always outweighs it.
_WEEKDAY = {
    5: 8, 6: 18, 7: 30, 8: 34, 9: 28, 10: 20, 11: 17, 12: 26, 13: 30,
    14: 19, 15: 22, 16: 38, 17: 76, 18: 100, 19: 88, 20: 58, 21: 32, 22: 14, 23: 6,
}
_SAT = {
    5: 4, 6: 6, 7: 10, 8: 22, 9: 44, 10: 62, 11: 70, 12: 58, 13: 44,
    14: 38, 15: 34, 16: 30, 17: 26, 18: 22, 19: 18, 20: 14, 21: 8, 22: 4, 23: 2,
}
_SUN = {
    5: 2, 6: 3, 7: 5, 8: 10, 9: 20, 10: 30, 11: 34, 12: 30, 13: 24,
    14: 20, 15: 18, 16: 16, 17: 14, 18: 12, 19: 10, 20: 8, 21: 5, 22: 3, 23: 1,
}
_WEEKDAY_BOOST = {0: 1.10, 1: 1.12, 2: 1.00, 3: 0.98, 4: 0.92, 5: None, 6: None}


def prior_index(weekday: int, hour: int) -> float:
    if weekday == 5:
        base = _SAT.get(hour, 30)
    elif weekday == 6:
        base = _SUN.get(hour, 20)
    else:
        base = _WEEKDAY.get(hour, 20) * _WEEKDAY_BOOST[weekday]
    return float(base)


PRIOR_WEIGHT = 3.0  # pseudo-observations behind the prior


def blended_profile(conn: sqlite3.Connection) -> dict[tuple[int, int], dict]:
    """Blend measured medians with the prior, per (weekday, hour)."""
    rows = conn.execute(
        "SELECT weekday, hour, people FROM readings WHERE people >= 0"
    ).fetchall()
    obs: dict[tuple[int, int], list[int]] = {}
    for wd, hr, ppl in rows:
        obs.setdefault((wd, hr), []).append(ppl)

    # normalise observations to the same 0-100 scale the prior uses: anchor on
    # the busiest measured hour we have seen at this gym.
    all_medians = {k: median(v) for k, v in obs.items()}
    scale = max(all_medians.values()) if all_medians else 0

    out = {}
    for wd in range(7):
        for hr in range(5, 24):
            vals = obs.get((wd, hr), [])
            prior = prior_index(wd, hr)
            if vals and scale > 0:
                measured_index = (median(vals) / scale) * 100.0
                n = len(vals)
                score = (measured_index * n + prior * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT)
                est_people = median(vals)
            else:
                n = 0
                score = prior
                est_people = None
            confidence = (
                "measured" if n >= 6 else
                "emerging" if n >= 3 else
                "early" if n >= 1 else
                "modelled"
            )
            out[(wd, hr)] = {
                "score": score, "n": n, "confidence": confidence,
                "people": est_people, "prior": prior,
            }
    return out


def label(score: float) -> str:
    if score <= 18:
        return "dead quiet"
    if score <= 32:
        return "quiet"
    if score <= 50:
        return "easy"
    if score <= 68:
        return "busy"
    if score <= 85:
        return "very busy"
    return "peak — avoid"


def windows(profile: dict, weekday: int, hours: list[int], span: int = 2) -> list[dict]:
    """Best contiguous windows of `span` hours for a weekday."""
    out = []
    for start in hours:
        if start + span > 24:
            continue
        slots = [profile[(weekday, h)] for h in range(start, start + span)]
        out.append({
            "start": start,
            "end": start + span,
            "score": sum(s["score"] for s in slots) / span,
            "min_conf": min(s["confidence"] for s in slots),
            "n": min(s["n"] for s in slots),
            "people": max((s["people"] or 0) for s in slots),
        })
    out.sort(key=lambda w: w["score"])
    return out


DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def resolve_day(arg: str | None) -> int:
    now = london_now()
    if not arg or arg == "today":
        return now.weekday()
    if arg == "tomorrow":
        return (now + timedelta(days=1)).weekday()
    low = arg.lower()[:3]
    for i, d in enumerate(DOW):
        if d.lower().startswith(low):
            return i
    raise SystemExit(f"unknown day: {arg}")


def cmd_advise(day: str | None, top: int = 3, all_hours: bool = False) -> int:
    conn = db()
    prof = blended_profile(conn)
    total = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    wk = resolve_day(day)
    print(f"# {DOW[wk]} — best {top} windows (observations: {total})")
    hours = list(range(5, 23)) if all_hours else list(range(6, 22))
    ranked = windows(prof, wk, hours, span=2)
    seen = set()
    shown = 0
    for w in ranked:
        if shown >= top:
            break
        if any(h in seen for h in range(w["start"], w["end"])):
            continue
        for h in range(w["start"], w["end"]):
            seen.add(h)
        ppl = f", ~{int(w['people'])} people" if (w["people"] and w["n"] >= 1) else ""
        print(f"{w['start']:02d}:00-{w['end']:02d}:00  {label(w['score']):10s} "
              f"index {w['score']:5.1f}{ppl}  [{w['min_conf']}, n={w['n']}]")
        shown += 1
    print("\nbusiest:")
    shown = 0
    for w in ranked[::-1]:
        if shown >= 3:
            break
        if any(h in seen for h in range(w["start"], w["end"])):
            continue
        for h in range(w["start"], w["end"]):
            seen.add(h)
        print(f"{w['start']:02d}:00-{w['end']:02d}:00  {label(w['score']):10s} index {w['score']:5.1f}")
        shown += 1
    conn.close()
    return 0


def cmd_stats() -> int:
    conn = db()
    rows = conn.execute(
        "SELECT weekday, hour, COUNT(*), MIN(people), MAX(people),"
        " CAST(AVG(people) AS INT) FROM readings GROUP BY weekday, hour"
        " ORDER BY weekday, hour"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    misses = conn.execute("SELECT COUNT(*) FROM misses").fetchone()[0]
    span = conn.execute("SELECT MIN(ts_local), MAX(ts_local) FROM readings").fetchone()
    if not total or not span or not span[0]:
        print(f"readings: 0  counter-nulls: {misses}  (no data yet — run sample)")
        conn.close()
        return 0
    print(f"readings: {total}  window: {span[0]} -> {span[1]}  counter-nulls: {misses}")
    print(f"{'day':9s} {'hour':>4s} {'n':>3s} {'min':>5s} {'max':>5s} {'avg':>5s}")
    for wd, hr, n, mn, mx, av in rows:
        print(f"{DOW[wd]:9s} {hr:4d} {n:3d} {mn:5d} {mx:5d} {av:5d}")
    conn.close()
    return 0


def cmd_report(day: str | None, all_hours: bool = False) -> int:
    conn = db()
    prof = blended_profile(conn)
    total = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    wk = resolve_day(day or "today")
    live: Any = None
    live_failed = False
    try:
        live = attendance(selected_gym()["Id"]).get("TotalPeopleInGym")
    except Exception:
        live_failed = True
    ranked = windows(prof, wk, list(range(5, 23)) if all_hours else list(range(6, 22)), span=2)
    best = []
    seen = set()
    for w in ranked:
        if len(best) >= 2:
            break
        if any(h in seen for h in range(w["start"], w["end"])):
            continue
        for h in range(w["start"], w["end"]):
            seen.add(h)
        best.append(w)
    worst = ranked[-1]

    lines = [f"🏋️ *{DOW[wk]}*"]
    if live is not None:
        lines.append(f"Right now: {live} people in the gym.")
    elif live_failed:
        lines.append("_Live count unavailable — credentials or API need checking._")
    for w in best:
        ppl = f" (~{int(w['people'])} people)" if (w["people"] and w["n"] >= 1) else ""
        conf = {"measured": "solid data", "emerging": "building data",
                "early": "early signal", "modelled": "modelled — still learning this slot"}[w["min_conf"]]
        lines.append(f"• {w['start']:02d}:00–{w['end']:02d}:00 — {label(w['score'])}{ppl} · {conf}")
    ppl = f" (~{int(worst['people'])} people)" if (worst["people"] and worst["n"] >= 1) else ""
    worst_label = label(worst["score"]).replace(" — avoid", "")
    if worst["score"] > 50:
        lines.append(f"⚠️ Avoid {worst['start']:02d}:00–{worst['end']:02d}:00 — {worst_label}{ppl}")
    else:
        # a "worst" window that is still quiet is not worth a warning
        lines.append(f"✅ No peak to dodge — busiest is {worst['start']:02d}:00–{worst['end']:02d}:00, "
                     f"only {worst_label}{ppl}")
    if total < 40:
        lines.append(f"_Only {total} readings so far — a slot needs six to become measured._")
    print("\n".join(lines))
    conn.close()
    return 0


def _mask_email(email: str) -> str:
    if not email:
        return "(unset)"
    if "@" not in email:
        return "(set)"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


def cmd_visits(limit: int = 10) -> int:
    """The member's own recent visits — attendance history, not the gym's."""
    d = api_get("/api/v2/gymSessions/member")
    if not isinstance(d, dict):
        print("unexpected response from gymSessions/member")
        return 1
    visits = d.get("Visits") or []
    total = (d.get("Summary") or {}).get("Total") or {}
    print(f"visits: {total.get('Visits', len(visits))} "
          f"({total.get('Duration', 0)} min total)")
    for v in visits[:limit]:
        gym = (v.get("Gym") or {}).get("Name") or "?"
        start = v.get("StartTime") or "?"
        minutes = v.get("Duration")
        when = start.replace("T", " ")[:16]
        print(f"{when}  {gym:24s} {minutes if minutes is not None else '?'} min")
    return 0


def cmd_doctor() -> int:
    """Prove the install works. Records no reading and caches no token."""
    global PERSIST_TOKEN
    PERSIST_TOKEN = False
    print(f"config file:  {CONFIG_FILE} ({'found' if os.path.exists(CONFIG_FILE) else 'absent'})")
    print(f"data dir:     {DATA_DIR}")
    print(f"member email: {_mask_email(MEMBER_EMAIL)}")
    print(f"credentials:  {secret_backend()}")
    try:
        pin = member_pin()
        print(f"PIN:          resolved ({len(pin)} chars, value not printed)")
    except Exception as exc:  # noqa: BLE001
        print(f"PIN:          FAILED — {exc}")
        return 1
    try:
        gym = selected_gym()
        a = attendance(gym["Id"])
    except Exception as exc:  # noqa: BLE001
        print(f"API:          FAILED — {type(exc).__name__}: {str(exc)[:120]}")
        return 1
    people = _as_int(a.get("TotalPeopleInGym"))
    print(f"gym:          {gym.get('Name')} (id {gym.get('Id')})")
    print(f"live count:   {people if people is not None else 'null — counter offline'}"
          f" at {a.get('AttendanceTime')}")
    print(f"database:     {DB_PATH} ({'present' if os.path.exists(DB_PATH) else 'not created yet'})")
    print("\nOK — `puregym.py sample` will record this reading.")
    return 0


def main(argv: list[str]) -> int:
    # one clean error line for the scheduler's log — no traceback unless -v
    try:
        return _main(argv)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        if os.environ.get("PUREGYM_DEBUG"):
            raise
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def _main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = argv[1] if len(argv) > 1 else "report"
    args = argv[2:]
    day = None
    top = 3
    all_hours = False
    i = 0
    while i < len(args):
        if args[i] == "--day" and i + 1 < len(args):
            day = args[i + 1]; i += 2
        elif args[i] == "--top" and i + 1 < len(args):
            top = int(args[i + 1]); i += 2
        elif args[i] == "--all-hours":
            all_hours = True; i += 1
        else:
            day = args[i]; i += 1
    if cmd == "doctor":
        return cmd_doctor()
    if cmd == "sample":
        return cmd_sample()
    if cmd == "advise":
        return cmd_advise(day, top, all_hours)
    if cmd == "report":
        return cmd_report(day, all_hours)
    if cmd == "stats":
        return cmd_stats()
    if cmd == "visits":
        return cmd_visits(top)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
