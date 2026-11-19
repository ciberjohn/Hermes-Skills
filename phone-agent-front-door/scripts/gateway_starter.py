#!/usr/bin/env python3
"""Minimal Twilio voice gateway: a menu in front of your own agent.

The smallest working version of the pattern: answer the call fast, check who is
calling, verify the request really came from Twilio, and only then hand the caller
to something that costs money or carries authority.

Rules baked in here, each one there because the obvious version gets it wrong:
  * The gate fails closed. No allowlist means it refuses to start.
  * The lockout is enforced on every PIN attempt, not only when entering the PIN.
  * The prompt lives inside <Gather>, so the caller hears it and can interrupt.
  * The model is never awaited inside a webhook; the caller hears a holding phrase
    and the answer arrives on a second request.
  * Nothing is logged that contains the caller's content.

Run it:
    python3 gateway_starter.py
Point the number's Voice webhook (POST) at https://<your-host>/voice
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
import uvicorn

STATE_DIR = Path(os.environ.get("PHONE_AGENT_DATA", "~/.local/share/phone-agent")).expanduser()
ATTEMPTS = STATE_DIR / "attempts.json"
MAX_BODY = 64 * 1024


# ------------------------------------------------------------------ secrets
def read_secret(name: str) -> str:
    """Resolve a value without ever printing it.

    Order: command hook (any vault), then a 0600 file, then the environment. The
    hook runs as an argv rather than through a shell, and a timeout returns empty
    instead of raising, because an exception's text can contain the command and so
    the secret itself.
    """
    cmd_var = f"{name}_CMD"
    raw_cmd = os.environ.get(cmd_var)
    if raw_cmd:
        try:
            proc = subprocess.run(shlex.split(raw_cmd), capture_output=True,
                                  text=True, timeout=20, shell=False)
        except subprocess.TimeoutExpired:
            print(f"[secret] {cmd_var} timed out", file=sys.stderr)
            return ""
        except (OSError, ValueError) as exc:
            print(f"[secret] {cmd_var} could not run ({exc.__class__.__name__})",
                  file=sys.stderr)
            return ""
        if proc.returncode != 0:
            # Exit code only: a vault CLI can print the secret in an error message.
            print(f"[secret] {cmd_var} exited {proc.returncode}", file=sys.stderr)
            return ""
        return proc.stdout.strip()

    file_var = f"{name}_FILE"
    if os.environ.get(file_var):
        path = Path(os.environ[file_var]).expanduser()
        if not path.exists():
            print(f"[secret] {file_var} points at a missing file", file=sys.stderr)
            return ""
        mode = path.stat().st_mode & 0o777
        if mode & 0o077:
            sys.exit(f"refusing {path}: mode {oct(mode)} is readable by others; chmod 600 it")
        return path.read_text().strip()

    if os.environ.get(name):
        print(f"[secret] {name} came from the environment; prefer {cmd_var} or {file_var}",
              file=sys.stderr)
        return os.environ[name].strip()
    return ""


def required(name: str) -> str:
    value = read_secret(name)
    if not value:
        sys.exit(f"missing {name}: set {name}_CMD, {name}_FILE, or {name}")
    return value


TOKEN = required("PHONE_AGENT_TWILIO_AUTH_TOKEN")
PIN = required("PHONE_AGENT_PIN")
PUBLIC_URL = read_secret("PHONE_AGENT_PUBLIC_URL").rstrip("/")

if not (PIN.isdigit() and 6 <= len(PIN) <= 10):
    sys.exit("PHONE_AGENT_PIN must be 6 to 10 digits: the keypad gather uses its length")
PIN_DIGITS = len(PIN)

ALLOW = {n.strip() for n in read_secret("PHONE_AGENT_ALLOWLIST").split(",") if n.strip()}
if not ALLOW and os.environ.get("PHONE_AGENT_ALLOW_ANY") != "1":
    sys.exit("PHONE_AGENT_ALLOWLIST is empty. Set at least one E.164 number, or set "
             "PHONE_AGENT_ALLOW_ANY=1 to accept that anyone who finds the number "
             "reaches the menu.")
for _number in ALLOW:
    if not re.fullmatch(r"\+[1-9]\d{6,14}", _number):
        sys.exit(f"allowlist entry {_number!r} is not E.164 (for example +15550000001)")

VOICE = os.environ.get("PHONE_AGENT_VOICE", "Polly.Amy-Neural")
LANG = os.environ.get("PHONE_AGENT_LANGUAGE", "en-GB")
for _label, _value in (("voice", VOICE), ("language", LANG)):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", _value):
        sys.exit(f"PHONE_AGENT_{_label.upper()} may contain only letters, digits, dot and dash")

PIN_TRIES = max(1, int(os.environ.get("PHONE_AGENT_PIN_TRIES", "3")))
LOCKOUT_SECONDS = max(60, int(os.environ.get("PHONE_AGENT_LOCKOUT_SECONDS", "3600")))
SESSION_TTL = 900

HOST = (os.environ.get("PHONE_AGENT_HOST") or "127.0.0.1").strip()
if HOST not in ("127.0.0.1", "localhost", "::1"):
    sys.exit(f"refusing to bind {HOST!r}: keep the origin on loopback and put a proxy in front")

STATE_DIR.mkdir(parents=True, exist_ok=True)
try:
    STATE_DIR.chmod(0o700)
except OSError:
    pass


# ------------------------------------------------------------------ signature
def candidate_urls(request: Request) -> list[str]:
    """Every plausible reading of the URL Twilio signed.

    Behind a proxy the origin can see plain http for a call made over https, and the
    host can arrive in one of several headers. Twilio signed exactly one of these;
    test the small set instead of betting on one.
    """
    path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    protos = {(request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower(),
              request.url.scheme, "https"}
    hosts = {(request.headers.get("x-forwarded-host") or "").split(",")[0].strip(),
             (request.headers.get("host") or "").strip(), request.url.netloc}
    if PUBLIC_URL:
        hosts.add(urllib.parse.urlsplit(PUBLIC_URL).netloc)
    return [f"{p}://{h}{path}" for p in sorted(x for x in protos if x)
            for h in sorted(x for x in hosts if x)]


def signature_ok(request: Request, form: dict) -> bool:
    supplied = request.headers.get("x-twilio-signature", "")
    if not supplied:
        return False
    suffix = "".join(k + form[k] for k in sorted(form))
    for url in candidate_urls(request):
        digest = hmac.new(TOKEN.encode(), (url + suffix).encode(), hashlib.sha1).digest()
        if hmac.compare_digest(base64.b64encode(digest).decode(), supplied):
            return True
    return False


# ------------------------------------------------------------------ attempt state
_LOCK = threading.Lock()


def _load() -> dict:
    try:
        return json.loads(ATTEMPTS.read_text())
    except FileNotFoundError:
        return {}
    except ValueError:
        print("[state] attempts.json is unreadable; treating as empty", file=sys.stderr)
        return {}


def _save(data: dict) -> None:
    tmp = ATTEMPTS.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh)
    os.replace(tmp, ATTEMPTS)


def locked_for(caller: str) -> int:
    with _LOCK:
        until = float(_load().get(caller, {}).get("locked_until", 0))
    return max(0, int(until - time.time()))


def register_failure(caller: str) -> tuple[int, bool]:
    """Record a wrong PIN. Returns (attempts_left, now_locked)."""
    with _LOCK:
        data = _load()
        rec = data.setdefault(caller, {"count": 0, "locked_until": 0})
        rec["count"] += 1
        locked = rec["count"] >= PIN_TRIES
        if locked:
            rec["locked_until"] = time.time() + LOCKOUT_SECONDS
            rec["count"] = 0
        # Prune expired, unused entries so spoofed numbers cannot grow the file.
        for key in [k for k, v in data.items()
                    if not v.get("count") and float(v.get("locked_until", 0)) < time.time()]:
            data.pop(key, None)
        data[caller] = rec
        _save(data)
        return (0 if locked else PIN_TRIES - rec["count"]), locked


def clear_failures(caller: str) -> None:
    with _LOCK:
        data = _load()
        data.pop(caller, None)
        _save(data)


# ------------------------------------------------------------------ session tokens
def mint(sid: str) -> str:
    exp = int(time.time()) + SESSION_TTL
    sig = hmac.new(TOKEN.encode(), f"{sid}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{exp}.{sig}"


def token_ok(token: str, sid: str) -> bool:
    try:
        exp_s, sig = token.split(".", 1)
        exp = int(exp_s)
    except (ValueError, AttributeError):
        return False
    if exp < time.time():
        return False
    good = hmac.new(TOKEN.encode(), f"{sid}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(good, sig)


# ------------------------------------------------------------------ twiml
def xml_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def say(text: str) -> str:
    return f'<Say voice="{VOICE}" language="{LANG}">{xml_text(text)}</Say>'


def gather(action: str, prompt: str, digits: int = 1) -> str:
    """The prompt goes INSIDE the gather, so it is heard and can be interrupted.

    A self-closing <Gather/> plays nothing and gives the caller seconds of silence.
    """
    return (f'<Gather action="{action}" method="POST" numDigits="{digits}" '
            f'timeout="7" finishOnKey="#">{say(prompt)}</Gather>')


def gather_speech(action: str, prompt: str) -> str:
    return (f'<Gather action="{action}" method="POST" input="speech" '
            f'speechTimeout="auto" language="{LANG}">{say(prompt)}</Gather>')


def response(*parts: str) -> Response:
    body = f'<?xml version="1.0" encoding="UTF-8"?><Response>{"".join(parts)}</Response>'
    return Response(content=body, media_type="application/xml")


MENU = ("One for status. Two for the second thing. Four to speak with the agent. "
        "Nine to repeat this menu.")


# ------------------------------------------------------------------ your code
def status_text() -> str:
    """Digit 1. Read a cache; never call a model mid-call.

    Replace this before exposing the number. A confident-sounding stub is worse than
    nothing, because it is indistinguishable from a real answer.
    """
    return "Status is not configured yet."


def second_text() -> str:
    """Digit 2. Anything else answerable from a local read."""
    return "That option is not configured yet."


def answer(question: str) -> str:
    """Digit 4, after the PIN. The only slow path, and it is opt-in.

    Runs off the request thread, so a slow agent never holds a webhook open. Keep
    the tool surface read-only: a keypad code proves the caller knows a code, not
    that they may act in your name.
    """
    return "The agent is not wired up yet."


# ------------------------------------------------------------------ app
app = FastAPI()
POOL = ThreadPoolExecutor(max_workers=4)
JOBS: dict[str, dict] = {}


async def parse(request: Request) -> dict | None:
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip()
    if ctype and ctype != "application/x-www-form-urlencoded":
        return None
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY:
        return None
    raw_bytes = await request.body()
    if len(raw_bytes) > MAX_BODY:
        return None
    raw = raw_bytes.decode("utf-8", "replace")
    # keep_blank_values matters: Twilio signs empty parameters too.
    return {k: v[0] for k, v in
            urllib.parse.parse_qs(raw, keep_blank_values=True).items()}


def authorised(form: dict) -> tuple[str, str | None]:
    """One place for the caller check, so no handler can forget it."""
    caller = form.get("From", "")
    if ALLOW and caller not in ALLOW:
        return caller, "This line is private. Goodbye."
    return caller, None


@app.post("/voice")
async def voice(request: Request):
    form = await parse(request)
    if form is None:
        return Response(status_code=413)
    if not signature_ok(request, form):
        # No request-derived fields: the body is unauthenticated at this point.
        print("[voice] rejected an unverified request", file=sys.stderr)
        return response(say("Goodbye."), "<Hangup/>")
    _, refusal = authorised(form)
    if refusal:
        return response(say(refusal), "<Hangup/>")
    return response(gather("/menu", MENU))


@app.post("/menu")
async def menu(request: Request):
    form = await parse(request)
    if form is None:
        return Response(status_code=413)
    if not signature_ok(request, form):
        return response(say("Goodbye."), "<Hangup/>")
    caller, refusal = authorised(form)
    if refusal:
        return response(say(refusal), "<Hangup/>")

    digit = (form.get("Digits") or "").strip()
    if digit == "1":
        return response(gather("/menu", f"{status_text()} {MENU}"))
    if digit == "2":
        return response(gather("/menu", f"{second_text()} {MENU}"))
    if digit == "9":
        return response(gather("/menu", MENU))
    if digit == "4":
        wait = locked_for(caller)
        if wait:
            return response(say(f"That number is locked for {max(1, wait // 60)} minutes."),
                            "<Hangup/>")
        return response(gather("/pin", "Enter your code, then press hash.",
                               digits=PIN_DIGITS))
    return response(gather("/menu", "I did not catch that. " + MENU))


@app.post("/pin")
async def pin(request: Request):
    form = await parse(request)
    if form is None:
        return Response(status_code=413)
    if not signature_ok(request, form):
        return response(say("Goodbye."), "<Hangup/>")
    caller, refusal = authorised(form)
    if refusal:
        return response(say(refusal), "<Hangup/>")

    # Checked here as well as at digit 4: entering the PIN loop must not buy
    # unlimited attempts inside one call.
    wait = locked_for(caller)
    if wait:
        return response(say(f"That number is locked for {max(1, wait // 60)} minutes."),
                        "<Hangup/>")

    supplied = (form.get("Digits") or "").strip()
    if hmac.compare_digest(supplied, PIN):
        clear_failures(caller)
        sid = form.get("CallSid", "")
        return response(gather_speech(f"/ask?t={mint(sid)}", "What do you need?"))

    left, locked = register_failure(caller)
    if locked:
        return response(say(f"Too many attempts. Locked for "
                            f"{max(1, LOCKOUT_SECONDS // 60)} minutes. Goodbye."), "<Hangup/>")
    return response(gather("/pin", f"That is not right. {left} "
                                   f"attempt{'s' if left != 1 else ''} left. Try again.",
                           digits=PIN_DIGITS))


def _work(sid: str, question: str) -> None:
    try:
        JOBS[sid] = {"text": answer(question), "done": True}
    except Exception:  # noqa: BLE001
        JOBS[sid] = {"text": "Something failed on my side.", "done": True}


@app.post("/ask")
async def ask(request: Request):
    form = await parse(request)
    if form is None:
        return Response(status_code=413)
    if not signature_ok(request, form):
        return response(say("Goodbye."), "<Hangup/>")
    _, refusal = authorised(form)
    if refusal:
        return response(say(refusal), "<Hangup/>")

    sid = form.get("CallSid", "")
    token = request.query_params.get("t", "")
    if not token_ok(token, sid):
        return response(say("That session has expired. Please start again."), "<Hangup/>")

    question = (form.get("SpeechResult") or "").strip()
    if not question:
        return response(gather_speech(f"/ask?t={token}", "I did not catch that."))

    JOBS[sid] = {"text": "", "done": False}
    POOL.submit(_work, sid, question)
    return response(say("One moment."),
                    f'<Redirect method="POST">/result?t={token}</Redirect>')


@app.post("/result")
async def result(request: Request):
    form = await parse(request)
    if form is None:
        return Response(status_code=413)
    if not signature_ok(request, form):
        return response(say("Goodbye."), "<Hangup/>")
    _, refusal = authorised(form)
    if refusal:
        return response(say(refusal), "<Hangup/>")

    sid = form.get("CallSid", "")
    token = request.query_params.get("t", "")
    if not token_ok(token, sid):
        return response(say("That session has expired. Please start again."), "<Hangup/>")

    job = JOBS.get(sid)
    if not job or not job.get("done"):
        return response('<Pause length="2"/>',
                        f'<Redirect method="POST">/result?t={token}</Redirect>')
    JOBS.pop(sid, None)
    return response(gather("/menu", f"{job['text']} {MENU}"))


@app.get("/health")
async def health():
    # Deliberately says nothing about the gate: this endpoint is reachable through
    # the same proxy as the webhook.
    return {"ok": True}


if __name__ == "__main__":
    port = int(os.environ.get("PHONE_AGENT_PORT", "8097"))
    print(f"listening on http://{HOST}:{port}")
    uvicorn.run(app, host=HOST, port=port, log_level="info")
