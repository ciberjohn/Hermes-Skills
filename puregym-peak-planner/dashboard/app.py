#!/usr/bin/env python3
"""PureGym quiet-hours dashboard — stdlib only (no pip deps).

Serves a single-page, mobile-first dashboard over a read-only copy of the
attendance database that the sampler pushes here every so often.

Bind: 127.0.0.1:8099 (put it behind a private-network reverse proxy such as
`tailscale serve`; never expose it to the internet).
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import median
from urllib.parse import parse_qs, urlparse

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Europe/London")
except Exception:  # pragma: no cover
    TZ = timezone.utc

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "puregym.sqlite"
HOST = (os.environ.get("DASH_HOST") or "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.environ.get("DASH_PORT", "8099"))
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
# Binding anywhere but loopback puts live headcount on the network. Refuse
# unless the operator says so explicitly.
if HOST not in LOOPBACK and os.environ.get("PUREGYM_ALLOW_REMOTE_BIND", "") not in ("1", "true", "yes"):
    raise SystemExit(
        f"refusing to bind {HOST}: this app has no authentication. "
        "Keep DASH_HOST=127.0.0.1 and publish it over Tailscale/WireGuard, "
        "or set PUREGYM_ALLOW_REMOTE_BIND=1 if you really mean it."
    )

DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _env_int(name: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except (TypeError, ValueError):
        return default

# ---- prior curve (same model as the sampler's advisor) ----------------------
_WEEKDAY = {5: 8, 6: 18, 7: 30, 8: 34, 9: 28, 10: 20, 11: 17, 12: 26, 13: 30,
            14: 19, 15: 22, 16: 38, 17: 76, 18: 100, 19: 88, 20: 58, 21: 32,
            22: 14, 23: 6}
_SAT = {5: 4, 6: 6, 7: 10, 8: 22, 9: 44, 10: 62, 11: 70, 12: 58, 13: 44,
        14: 38, 15: 34, 16: 30, 17: 26, 18: 22, 19: 18, 20: 14, 21: 8, 22: 4, 23: 2}
_SUN = {5: 2, 6: 3, 7: 5, 8: 10, 9: 20, 10: 30, 11: 34, 12: 30, 13: 24,
        14: 20, 15: 18, 16: 16, 17: 14, 18: 12, 19: 10, 20: 8, 21: 5, 22: 3, 23: 1}
_BOOST = {0: 1.10, 1: 1.12, 2: 1.00, 3: 0.98, 4: 0.92}
PRIOR_WEIGHT = 3.0
HOUR_FROM, HOUR_TO = 5, 23


def prior(weekday: int, hour: int) -> float:
    if weekday == 5:
        return float(_SAT.get(hour, 30))
    if weekday == 6:
        return float(_SUN.get(hour, 20))
    return float(_WEEKDAY.get(hour, 20) * _BOOST.get(weekday, 1.0))


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
    return "peak"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def load_readings(conn: sqlite3.Connection, since: datetime | None = None):
    q = "SELECT ts_utc, ts_local, weekday, hour, people, classes FROM readings"
    args: list = []
    if since is not None:
        q += " WHERE ts_utc >= ?"
        args.append(since.astimezone(timezone.utc).isoformat(timespec="seconds"))
    q += " ORDER BY ts_utc"
    return conn.execute(q, args).fetchall()


def profile(conn: sqlite3.Connection) -> dict:
    rows = load_readings(conn)
    obs: dict[tuple[int, int], list[int]] = {}
    for r in rows:
        obs.setdefault((r["weekday"], r["hour"]), []).append(r["people"])
    medians = {k: median(v) for k, v in obs.items()}
    scale = max(medians.values()) if medians else 0

    out = {}
    for wd in range(7):
        cells = []
        for hr in range(HOUR_FROM, HOUR_TO + 1):
            vals = obs.get((wd, hr), [])
            p = prior(wd, hr)
            if vals and scale > 0:
                n = len(vals)
                measured = median(vals) / scale * 100.0
                score = (measured * n + p * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT)
                people = median(vals)
            else:
                n, score, people = 0, p, None
            cells.append({
                "h": hr,
                "score": round(score, 1),
                "n": n,
                "people": people,
                "conf": "measured" if n >= 6 else "emerging" if n >= 3 else "early" if n else "modelled",
                "label": label(score),
            })
        out[wd] = cells
    return out


def rank_windows(cells: list[dict], span: int = 2, hour_from: int = 6, hour_to: int = 22) -> list[dict]:
    """All `span`-hour windows between hour_from and hour_to, quietest first."""
    cands = []
    for i in range(len(cells) - span + 1):
        chunk = cells[i:i + span]
        if chunk[0]["h"] < hour_from or chunk[-1]["h"] + 1 > hour_to:
            continue
        cands.append({
            "start": chunk[0]["h"],
            "end": chunk[-1]["h"] + 1,
            "score": round(sum(c["score"] for c in chunk) / span, 1),
            "label": label(sum(c["score"] for c in chunk) / span),
            "n": min(c["n"] for c in chunk),
            "conf": min((c["conf"] for c in chunk), key=["modelled", "early", "emerging", "measured"].index),
            "people": max((c["people"] or 0) for c in chunk) or None,
        })
    cands.sort(key=lambda w: w["score"])
    return cands


def pick_windows(cands: list[dict], top: int = 3) -> list[dict]:
    """Top non-overlapping windows from a ranked list."""
    picked, used = [], set()
    for w in cands:
        if len(picked) >= top:
            break
        if any(h in used for h in range(w["start"], w["end"])):
            continue
        picked.append(w)
        used.update(range(w["start"], w["end"]))
    return picked


def overview() -> dict:
    now = datetime.now(TZ)
    if not DB_PATH.exists():
        return {"ok": False, "error": "no database yet", "now": now.isoformat()}
    conn = connect()
    try:
        total = conn.execute("SELECT COUNT(*) c FROM readings").fetchone()["c"]
        span = conn.execute("SELECT MIN(ts_local) a, MAX(ts_local) b FROM readings").fetchone()
        last = conn.execute(
            "SELECT ts_local, people, classes FROM readings ORDER BY ts_utc DESC LIMIT 1"
        ).fetchone()
        prof = profile(conn)
        recent = load_readings(conn, now - timedelta(hours=48))
    finally:
        conn.close()

    today_cells = prof[now.weekday()]
    cur = next((c for c in today_cells if c["h"] == now.hour), today_cells[0])
    ranked = rank_windows(today_cells, 2, 6, 22)

    series = []
    buckets: dict[str, list[int]] = {}
    order: list[str] = []
    for r in recent:
        t = datetime.fromisoformat(r["ts_local"])
        key = t.replace(minute=0, second=0, microsecond=0).isoformat()
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(r["people"])
    for key in order:
        vals = buckets[key]
        series.append({"t": key, "v": round(sum(vals) / len(vals), 1), "n": len(vals)})

    peak = max((r["people"] for r in recent), default=0)
    return {
        "ok": True,
        "gym": {
            "name": os.environ.get("GYM_NAME", "PureGym"),
            "id": _env_int("GYM_ID", 0),
            "tz": os.environ.get("GYM_TZ", "Europe/London"),
        },
        "now": {
            "iso": now.isoformat(timespec="seconds"),
            "dow": now.weekday(),
            "hour": now.hour,
            "people": last["people"] if last else None,
            "classes": last["classes"] if last else 0,
            "as_of": last["ts_local"] if last else None,
            "score": cur["score"],
            "label": cur["label"],
        },
        "today": {
            "weekday": now.weekday(),
            "best": pick_windows(ranked, 3),
            "worst": ranked[-1] if ranked and ranked[-1]["score"] > 50 else None,
        },
        "week": [{"weekday": wd, "day": DOW[wd], "short": SHORT[wd], "cells": prof[wd]} for wd in range(7)],
        "series": series,
        "stats": {
            "readings": total,
            "first": span["a"] if span else None,
            "last": span["b"] if span else None,
            "peak_seen": peak,
        },
        "model": {"prior_weight": PRIOR_WEIGHT, "hours": [HOUR_FROM, HOUR_TO]},
    }


PAGE = r"""<!doctype html>
<html lang="en" data-theme="claude">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#141210">
<title>PureGym · quiet hours</title>
<style>
:root{
  --bg:#141210; --bg-2:#1a1715; --panel:#1d1a17; --line:#2a2521; --line-2:#37302a;
  --ink:#efe9e2; --ink-2:#b6aaa0; --ink-3:#7d7269;
  --accent:#d97757; --accent-soft:#3a2620; --ok:#7fa650; --warn:#d9a441; --bad:#c65f4e;
  --r:12px; --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  --sans:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;overflow-x:hidden;max-width:100%}
body{padding:env(safe-area-inset-top) 0 calc(env(safe-area-inset-bottom) + 18px);min-height:100dvh}
a{color:inherit}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px}
header{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.hrow{display:flex;align-items:center;gap:12px;padding:12px 0}
.brand{display:flex;align-items:center;gap:10px;min-width:0}
.logo{width:30px;height:30px;border-radius:9px;background:linear-gradient(150deg,#d97757,#8f4a34);
  display:grid;place-items:center;font:700 14px/1 var(--mono);color:#1a1210;flex:0 0 auto}
.brand h1{font:600 15px/1.15 var(--sans);margin:0;letter-spacing:-.01em;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.brand .sub{font:400 11.5px/1.3 var(--mono);color:var(--ink-3);white-space:nowrap}
.spacer{flex:1}
.pill{display:inline-flex;align-items:center;gap:7px;font:500 11.5px/1 var(--mono);
  padding:7px 10px;border:1px solid var(--line-2);border-radius:999px;color:var(--ink-2);
  background:var(--bg-2);white-space:nowrap}
.dot{width:7px;height:7px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 0 rgba(127,166,80,.5);
  animation:pulse 2.4s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(127,166,80,.45)}70%{box-shadow:0 0 0 7px rgba(127,166,80,0)}100%{box-shadow:0 0 0 0 rgba(127,166,80,0)}}
.iconbtn{border:1px solid var(--line-2);background:var(--bg-2);color:var(--ink-2);width:34px;height:34px;
  border-radius:10px;display:grid;place-items:center;cursor:pointer;transition:.15s}
.iconbtn:hover{color:var(--ink);border-color:#4a413a}
.iconbtn.spin svg{animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

main{padding-top:16px;display:grid;gap:14px;grid-template-columns:minmax(0,1fr)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:16px;min-width:0;max-width:100%}
.card h2{font:600 12px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3);margin:0 0 12px}

/* hero */
.hero{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:end}
.hero .big{font:600 clamp(34px,9vw,52px)/0.95 var(--mono);letter-spacing:-.03em;display:flex;align-items:baseline;gap:8px}
.hero .big small{font:500 13px/1 var(--mono);color:var(--ink-3);letter-spacing:0}
.hero .stat{font:500 12.5px/1.5 var(--mono);color:var(--ink-2);text-align:right}
.tag{display:inline-flex;align-items:center;gap:6px;font:500 11px/1 var(--mono);padding:5px 8px;
  border-radius:6px;background:var(--accent-soft);color:var(--accent);border:1px solid #4a2e25;text-transform:lowercase}
.meter{height:6px;border-radius:99px;background:#241f1b;overflow:hidden;margin-top:14px;position:relative}
.meter i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#7fa650,#d9a441 55%,#c65f4e);transition:width .6s ease}
.meter .mark{position:absolute;top:-3px;width:2px;height:12px;background:var(--ink);opacity:.55}

/* best window cards */
.grid3{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(215px,1fr))}
.win{background:var(--bg-2);border:1px solid var(--line);border-radius:10px;padding:12px;min-width:0}
.win .t{font:600 17px/1.1 var(--mono);letter-spacing:-.02em}
.win .l{margin-top:6px;font:500 11.5px/1 var(--mono);color:var(--ok);text-transform:lowercase}
.win .c{margin-top:7px;font:500 10.5px/1 var(--mono);color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.win.worst .l{color:var(--bad)}

/* heatmap */
.legend{display:flex;align-items:center;gap:8px;font:500 10.5px/1 var(--mono);color:var(--ink-3);margin-bottom:10px;flex-wrap:wrap}
.scale{display:flex;gap:2px}
.scale i{width:13px;height:9px;border-radius:2px;display:block}
.hm{overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;margin:0 -4px;padding:0 4px 2px;max-width:100%}
.hm table{border-collapse:separate;border-spacing:2px;width:100%;min-width:520px;table-layout:fixed}
.hm th{font:500 10px/1 var(--mono);color:var(--ink-3);text-align:center;padding:0 0 4px;font-weight:500}
.hm th.row{text-align:left;position:sticky;left:0;background:var(--panel);z-index:2;padding-right:6px;width:36px}
.hm td{padding:0}
.cell{height:26px;border-radius:5px;background:#241f1b;cursor:pointer;transition:transform .12s,outline-color .12s;
  outline:1px solid transparent;position:relative}
.cell:hover{transform:scale(1.14);outline-color:#6b5f55;z-index:3}
.cell.sel{outline:2px solid var(--accent);z-index:4}
.cell.now::after{content:"";position:absolute;inset:0;border:1.5px solid var(--ink);border-radius:5px;opacity:.85}
.hm tr.today th.row{color:var(--accent)}
.hm tr.today .cell{box-shadow:inset 0 -1px 0 rgba(217,119,87,.35)}

/* sparkline */
.spark{width:100%;height:104px;display:block;touch-action:pan-y}
.spark .area{fill:url(#grad);stroke:none}
.spark .line{fill:none;stroke:var(--accent);stroke-width:1.6;stroke-linejoin:round;stroke-linecap:round}
.spark .grid{stroke:#241f1b;stroke-width:1}
.spark .lbl{fill:var(--ink-3);font:9.5px var(--mono)}
.series-meta{display:flex;justify-content:space-between;font:500 10.5px/1 var(--mono);color:var(--ink-3);margin-top:6px}

/* detail sheet */
.backdrop{position:fixed;inset:0;background:rgba(0,0,0,.52);opacity:0;pointer-events:none;transition:opacity .2s;z-index:35}
.backdrop.on{opacity:1;pointer-events:auto}
.sheet{position:fixed;left:0;right:0;bottom:0;z-index:40;background:var(--bg-2);border-top:1px solid var(--line-2);
  border-radius:16px 16px 0 0;padding:16px 16px calc(20px + env(safe-area-inset-bottom));
  transform:translateY(110%);transition:transform .22s cubic-bezier(.2,.8,.2,1);box-shadow:0 -20px 60px rgba(0,0,0,.5)}
.sheet.open{transform:translateY(0)}
.sheet .grab{width:38px;height:4px;border-radius:9px;background:#3a332d;margin:0 auto 14px}
.sheet h3{margin:0 0 4px;font:600 16px/1.2 var(--sans)}
.sheet .kv{display:grid;grid-template-columns:1fr auto;gap:6px 12px;font:500 12.5px/1.5 var(--mono);color:var(--ink-2);margin-top:12px}
.sheet .kv b{color:var(--ink);font-weight:600}
.close{position:absolute;right:12px;top:12px}
footer{color:var(--ink-3);font:500 10.5px/1.6 var(--mono);padding:6px 2px 0;display:flex;gap:10px;flex-wrap:wrap}
.dotsep{opacity:.4}
.err{border-color:#5a3128;background:#241614;color:#e7b4a6}

/* mobile day view (only shown on small screens) */
.mob-only{display:none}
.mchips{display:flex;gap:6px;overflow-x:auto;padding:2px 0 12px;-webkit-overflow-scrolling:touch}
.mchip{flex:0 0 auto;padding:8px 11px;border-radius:9px;border:1px solid var(--line-2);background:var(--bg-2);
  color:var(--ink-2);font:500 11.5px/1 var(--mono);cursor:pointer}
.mchip.on{background:var(--accent-soft);border-color:#4a2e25;color:var(--accent)}
.mrow{display:grid;grid-template-columns:46px 1fr 82px;gap:10px;align-items:center;padding:10px 2px;
  border-bottom:1px solid #241f1b;cursor:pointer}
.mrow:last-child{border-bottom:0}
.mrow .h{font:500 12px/1 var(--mono);color:var(--ink-2)}
.mbar{height:9px;border-radius:9px;background:#241f1b;overflow:hidden}
.mbar i{display:block;height:100%;border-radius:9px}
.mrow .ml{font:500 10.5px/1.25 var(--mono);color:var(--ink-3);text-align:right}
.mrow.now .h{color:var(--accent)}

@media (max-width:640px){
  .mob-only{display:block}
  .hm{display:none}
  .legend .hint{display:none}
  .wrap{padding:0 12px}
  .brand .sub{display:none}
  .hero{grid-template-columns:1fr;align-items:start}
  .hero .stat{text-align:left}
  .grid3{grid-template-columns:1fr;gap:8px}
  .win{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:11px 12px}
  .win .t{flex:0 0 auto}
  .win .l{margin:0}
  .win .c{margin:0;max-width:48%}
  .card{padding:14px}
  .hm table{min-width:500px}
  .cell{height:30px}          /* bigger touch targets */
  .hm th.row{width:32px}
  header{position:sticky}
  .hrow{padding:10px 0}
}
@media (max-width:380px){
  .hero .big{font-size:34px}
  .pill span.txt{display:none}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<header>
  <div class="wrap hrow">
    <div class="brand">
      <div class="logo">PG</div>
      <div>
        <h1 id="gymName">PureGym</h1>
        <div class="sub" id="sub">live attendance · tailnet only</div>
      </div>
    </div>
    <div class="spacer"></div>
    <div class="pill"><i class="dot" id="dot"></i><span class="txt" id="updated">loading…</span></div>
    <button class="iconbtn" id="refresh" aria-label="Refresh" title="Refresh">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>
    </button>
  </div>
</header>

<main class="wrap">
  <section class="card">
    <div class="hero">
      <div>
        <h2>in the gym right now</h2>
        <div class="big"><span id="live">–</span><small>people</small></div>
      </div>
      <div class="stat">
        <span class="tag" id="nowLabel">–</span>
        <div style="margin-top:8px" id="asOf">–</div>
      </div>
    </div>
    <div class="meter" aria-hidden="true"><i id="meterFill" style="width:0%"></i><span class="mark" id="meterMark" style="left:0"></span></div>
    <div class="series-meta"><span id="meterNote">typical for this hour</span><span id="peakSeen"></span></div>
  </section>

  <section class="card">
    <h2>best windows today · <span id="todayName">–</span></h2>
    <div class="grid3" id="windows"></div>
  </section>

  <section class="card">
    <h2>week heatmap</h2>
    <div class="legend">
      <span>quiet</span>
      <div class="scale" id="scale"></div>
      <span>peak</span>
      <span class="hint" style="margin-left:auto">tap a cell for detail</span>
    </div>
    <div class="hm"><table id="hm"></table></div>
    <div class="mob-only">
      <div class="mchips" id="mchips"></div>
      <div id="mlist"></div>
    </div>
  </section>

  <section class="card">
    <h2>last 48 hours</h2>
    <svg class="spark" id="spark" viewBox="0 0 600 104" preserveAspectRatio="none" role="img" aria-label="Attendance trend"></svg>
    <div class="series-meta"><span id="sparkFrom">–</span><span id="sparkTo">–</span></div>
  </section>

  <footer>
    <span id="footStats">–</span>
    <span class="dotsep">·</span>
    <span>auto-refresh 60s</span>
    <span class="dotsep">·</span>
    <span>tailnet only</span>
  </footer>
</main>

<div class="backdrop" id="backdrop"></div>
<div class="sheet" id="sheet" aria-hidden="true">
  <div class="grab"></div>
  <button class="iconbtn close" id="sheetClose" aria-label="Close">✕</button>
  <h3 id="sheetTitle">–</h3>
  <div id="sheetSub" style="font:500 12px/1.4 var(--mono);color:var(--ink-3)">–</div>
  <div class="kv" id="sheetKv"></div>
</div>

<script>
const $ = s => document.querySelector(s);
const pad = n => String(n).padStart(2,'0');
const CONF = {measured:'measured',emerging:'building',early:'early',modelled:'modelled'};
let DATA = null, selected = null;

function colour(score, conf){
  // quiet = cool olive, peak = warm red — matches the meter gradient.
  // modelled cells are dimmed so real measurements visibly stand out.
  const stops = [[0,[127,166,80]],[45,[217,164,65]],[75,[198,95,78]],[100,[176,62,48]]];
  let a=stops[0], b=stops[stops.length-1];
  for(let i=0;i<stops.length-1;i++){ if(score>=stops[i][0] && score<=stops[i+1][0]){a=stops[i];b=stops[i+1];break;} }
  const t = (score-a[0])/((b[0]-a[0])||1);
  const c = a[1].map((v,i)=>Math.round(v+(b[1][i]-v)*t));
  const warm = 0.20 + Math.min(score,100)/100*0.62;
  const alpha = conf === 'modelled' ? warm*0.5 : warm;
  return `rgba(${c[0]},${c[1]},${c[2]},${alpha.toFixed(2)})`;
}

function renderScale(){
  const el = $('#scale'); el.innerHTML='';
  [0,20,40,60,80,100].forEach(s=>{ const i=document.createElement('i'); i.style.background=colour(s); el.appendChild(i); });
}

function renderWindows(d){
  const box = $('#windows'); box.innerHTML='';
  const list = [...d.today.best];
  if(d.today.worst && !list.some(w=>w.start===d.today.worst.start)) list.push({...d.today.worst, worst:true});
  list.forEach(w=>{
    const el=document.createElement('div');
    el.className='win'+(w.worst?' worst':'');
    el.innerHTML = `<div>
        <div class="t">${pad(w.start)}:00–${pad(w.end)}:00</div>
        <div class="l">${w.worst?'avoid · ':'best · '}${w.label}</div>
      </div>
      <div class="c">${w.people!==null?'~'+Math.round(w.people)+' people · ':''}${CONF[w.conf]||w.conf}</div>`;
    box.appendChild(el);
  });
}

function renderHeatmap(d){
  const t = document.createElement('table');
  const hours = d.model.hours;
  let head = '<thead><tr><th class="row"></th>';
  for(let h=hours[0]; h<=hours[1]; h++) head += `<th>${h%2===0?pad(h):''}</th>`;
  head += '</tr></thead>';
  let body = '<tbody>';
  d.week.forEach(row=>{
    const isToday = row.weekday === d.now.dow;
    body += `<tr class="${isToday?'today':''}"><th class="row">${row.short}</th>`;
    row.cells.forEach(c=>{
      body += `<td><div class="cell${isToday&&c.h===d.now.hour?' now':''}" data-wd="${row.weekday}" data-h="${c.h}"
        style="background:${colour(c.score,c.conf)}" title="${row.day} ${pad(c.h)}:00 · ${c.label} · n=${c.n}"></div></td>`;
    });
    body += '</tr>';
  });
  body += '</tbody>';
  t.innerHTML = head + body;
  const hm = $('#hm'); hm.innerHTML=''; hm.appendChild(t);
  hm.querySelectorAll('.cell').forEach(cell=>{
    cell.addEventListener('click', ()=> openSheet(+cell.dataset.wd, +cell.dataset.h));
  });
  if(selected) hm.querySelector(`.cell[data-wd="${selected.wd}"][data-h="${selected.h}"]`)?.classList.add('sel');
}

function renderSpark(series){
  const svg = $('#spark'); const W=600,H=104,P=6;
  if(series.length < 3){
    svg.innerHTML = `<text x="12" y="52" class="lbl">collecting — needs a few hours of readings</text>
      <text x="12" y="70" class="lbl">${series.length} hour${series.length===1?'':'s'} so far</text>`;
    $('#sparkFrom').textContent = series.length ? new Date(series[0].t).toLocaleString('en-GB',{weekday:'short',hour:'2-digit',minute:'2-digit'}) : '–';
    $('#sparkTo').textContent = '';
    return;
  }
  const max = Math.max(...series.map(s=>s.v), 1);
  const x = i => P + (W-2*P) * (series.length===1?0.5:i/(series.length-1));
  const y = v => H-P - (H-2*P) * (v/max);
  let pts = series.map((s,i)=>[x(i), y(s.v)]);
  let line = pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
  let area = `M${pts[0][0].toFixed(1)} ${H-P} ` + line.replace('M','L') + ` L${pts[pts.length-1][0].toFixed(1)} ${H-P} Z`;
  let grid='';
  for(let i=0;i<4;i++){ const gy=P+(H-2*P)*i/3; grid += `<line class="grid" x1="${P}" x2="${W-P}" y1="${gy.toFixed(1)}" y2="${gy.toFixed(1)}"/>`; }
  const peak = series.reduce((a,b)=>b.v>a.v?b:a, series[0]);
  svg.innerHTML = `<defs><linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#d97757" stop-opacity=".28"/>
      <stop offset="100%" stop-color="#d97757" stop-opacity="0"/></linearGradient></defs>
      ${grid}<path class="area" d="${area}"/><path class="line" d="${line}"/>
      <circle cx="${x(series.indexOf(peak)).toFixed(1)}" cy="${y(peak.v).toFixed(1)}" r="2.6" fill="#d97757"/>
      <text x="${P}" y="12" class="lbl">peak ${Math.round(peak.v)}</text>`;
  const f = s => new Date(s.t).toLocaleString('en-GB',{weekday:'short',hour:'2-digit',minute:'2-digit'});
  $('#sparkFrom').textContent = f(series[0]);
  $('#sparkTo').textContent = f(series[series.length-1]);
}

let mobDay = null;
function solid(score,conf){ return colour(score,conf).replace(/,([\d.]+)\)$/, ',0.95)'); }

function renderMobile(d){
  if(mobDay===null) mobDay = d.now.dow;
  const chips = $('#mchips'); chips.innerHTML='';
  d.week.forEach(row=>{
    const b=document.createElement('button');
    b.className='mchip'+(row.weekday===mobDay?' on':'');
    b.textContent=row.short;
    b.setAttribute('aria-pressed', row.weekday===mobDay);
    b.onclick=()=>{ mobDay=row.weekday; renderMobile(d); };
    chips.appendChild(b);
  });
  const list=$('#mlist'); list.innerHTML='';
  d.week[mobDay].cells.forEach(c=>{
    const el=document.createElement('div');
    el.className='mrow'+(mobDay===d.now.dow&&c.h===d.now.hour?' now':'');
    el.innerHTML=`<div class="h">${pad(c.h)}:00</div>
      <div class="mbar"><i style="width:${Math.max(3,Math.min(100,c.score))}%;background:${solid(c.score,c.conf)}"></i></div>
      <div class="ml">${c.people!==null?Math.round(c.people)+' ppl':c.label}<br>${CONF[c.conf]}</div>`;
    el.onclick=()=>openSheet(mobDay,c.h);
    list.appendChild(el);
  });
}

function openSheet(wd,h){
  const d = DATA; const row = d.week[wd]; const c = row.cells.find(x=>x.h===h);
  selected = {wd,h};
  document.querySelectorAll('.cell.sel').forEach(e=>e.classList.remove('sel'));
  document.querySelector(`.cell[data-wd="${wd}"][data-h="${h}"]`)?.classList.add('sel');
  $('#sheetTitle').textContent = `${row.day} · ${pad(h)}:00–${pad(h+1)}:00`;
  $('#sheetSub').textContent = `${c.label} · ${CONF[c.conf]}${c.n?` · ${c.n} samples`:''}`;
  $('#sheetKv').innerHTML = `
    <span>typical headcount</span><b>${c.people!==null?Math.round(c.people):'—'}</b>
    <span>relative busyness</span><b>${Math.round(c.score)}/100</b>
    <span>confidence</span><b>${CONF[c.conf]}</b>
    <span>samples here</span><b>${c.n}</b>`;
  $('#sheet').classList.add('open'); $('#backdrop').classList.add('on'); $('#sheet').setAttribute('aria-hidden','false');
}
function closeSheet(){ $('#sheet').classList.remove('open'); $('#backdrop').classList.remove('on'); $('#sheet').setAttribute('aria-hidden','true'); }
$('#backdrop').addEventListener('click', closeSheet);
$('#sheetClose').addEventListener('click', closeSheet);

function render(d){
  DATA = d;
  if(!d.ok){ $('#updated').textContent='no data'; $('#live').textContent='—'; return; }
  $('#gymName').textContent = d.gym.name;
  $('#live').textContent = d.now.people ?? '–';
  $('#nowLabel').textContent = `typical ${pad(d.now.hour)}:00 · ${d.now.label}`;
  const asof = d.now.as_of ? new Date(d.now.as_of) : null;
  const stale = asof && asof.toDateString() !== new Date().toDateString();
  const dayN = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  $('#asOf').innerHTML = asof
    ? `as of ${stale ? dayN[asof.getDay()]+' ' : ''}${pad(asof.getHours())}:${pad(asof.getMinutes())}`
    : '–';
  const ageMin = asof ? (Date.now() - asof.getTime())/60000 : null;
  if(ageMin !== null && ageMin > 45){
    $('#updated').textContent = `stale ${ageMin >= 90 ? Math.round(ageMin/60)+'h' : Math.round(ageMin)+'m'}`;
    $('#dot').style.background = '#d9a441';
    $('#dot').style.animation = 'none';
  }else{
    $('#updated').textContent = `${d.stats.readings} samples`;
    $('#dot').style.background = '';
    $('#dot').style.animation = '';
  }
  $('#meterFill').style.width = Math.min(100,d.now.score)+'%';
  // live headcount against the busiest value we've ever seen
  const peak = Math.max(d.stats.peak_seen,1);
  $('#meterNote').textContent = `${d.now.label} for this hour · index ${Math.round(d.now.score)}`;
  $('#meterMark').style.left = Math.min(100, (d.now.people||0)/peak*100)+'%';
  $('#peakSeen').textContent = d.stats.peak_seen ? `busiest seen ${d.stats.peak_seen}` : '';
  $('#todayName').textContent = d.week[d.now.dow].day;
  renderWindows(d); renderHeatmap(d); renderMobile(d); renderSpark(d.series||[]);
  const f = s => s ? new Date(s).toLocaleDateString('en-GB',{day:'2-digit',month:'short'}) : '—';
  $('#footStats').textContent = `${d.stats.readings} readings · since ${f(d.stats.first)}`;
}

async function load(spin){
  if(spin) $('#refresh').classList.add('spin');
  try{
    const r = await fetch('/api/overview', {cache:'no-store'});
    const d = await r.json();
    render(d);
  }catch(e){
    $('#updated').textContent = 'offline';
    $('#dot').style.background = '#c65f4e';
  }finally{ setTimeout(()=>$('#refresh').classList.remove('spin'), 400); }
}
$('#refresh').addEventListener('click', ()=>load(true));
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeSheet(); if(e.key==='r') load(true); });
renderScale(); load(false); setInterval(()=>load(false), 60000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "puregym-dash/1.0"

    def _send(self, code: int, body: bytes, ctype: str, cache: str = "no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "frame-ancestors 'none'",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            elif path == "/api/overview":
                body = json.dumps(overview()).encode()
                self._send(200, body, "application/json")
            elif path == "/healthz":
                self._send(200, b"ok", "text/plain")
            else:
                self._send(404, b"not found", "text/plain")
        except Exception as exc:  # noqa: BLE001
            # log the detail here; never hand paths or internals to the client
            print(f"error serving {path}: {type(exc).__name__}: {exc}", flush=True)
            payload = json.dumps({"ok": False, "error": "internal error"}).encode()
            self._send(500, payload, "application/json")

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


def main() -> None:
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    bound_host, bound_port = srv.server_address[0], srv.server_address[1]
    print(f"puregym dashboard on http://{bound_host}:{bound_port} db={DB_PATH}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
