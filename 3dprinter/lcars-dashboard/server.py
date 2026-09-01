#!/usr/bin/env python3
"""LCARS dashboard + proxy for the FlashForge AD5X printer.

Serves a Star Trek LCARS-styled dashboard and proxies the printer's API and
camera. The printer is reached at PRINTER_HOST (a direct address, or a relay
that forwards 8898/8899/8080 to the printer).

Configuration (env vars):
  PRINTER_HOST        host/ip serving the printer API + camera
                      (default: read from 3DPRINTER_STATE state file)
  PRINTER_SERIAL      printer serial number (default: state file)
  PRINTER_CHECK_CODE  printer check code   (default: state file)
  3DPRINTER_STATE     path to JSON state file: {"printer": {"host": .., "serial": .., "check_code": ..}}
  PORT                listen port (default 8890)
  BIND                bind address (default 0.0.0.0; use 127.0.0.1 with host networking)

COMMS (Spock chat bridge) env vars:
  DISCORD_BOT_TOKEN   bot token used to DM the one-time unlock code (Discord only)
  DISCORD_USER_ID     Discord user id that receives the unlock code DM
  API_SERVER_URL      Hermes api_server base URL (default http://host.docker.internal:8642/v1)
  API_SERVER_KEY      bearer key for the Hermes api_server
  OTP_TTL             unlock code lifetime, seconds (default 600)
  SESSION_TTL         chat session lifetime, seconds (default 86400)
  OTP_MIN_INTERVAL    min seconds between code requests (default 20)
  OTP_MAX_ATTEMPTS    max failed attempts before re-lock (default 5)

Replicator preview env vars:
  PREVIEW_MODELS_DIR  directory tree scanned for STL models (default "models")
  PREVIEW_CACHE_DIR   where generated GIFs are cached (default "preview_cache")
  PREVIEW_SIZE        GIF frame size px (default 320)
  PREVIEW_FRAMES      frames per rotation (default 24)
  PREVIEW_FPS         GIF speed (default 12)
  PREVIEW_TILT        camera elevation degrees (default 28)

NOTE: the AD5X only serves its local HTTP API (port 8898) when the printer is
in LAN-only mode (touchscreen: Settings -> WiFi -> Network Mode -> Local
Network Only). The camera stream (8080) only serves frames while actively
printing.

Endpoints:
  /            LCARS dashboard (index.html)
  /comms       stripped mobile chat page (comms.html)
  /comms.js    shared comms UI (chat window used by both pages)
  /api/status  JSON printer status (state, temps, layer, progress, ETA)
  /api/files   JSON last files on the printer
  /api/preview?file=<gcode>  JSON {ok, name, gif} — resolve a printing gcode
                             name to a local STL and report its preview GIF URL
  /preview/<stem>.gif  rotating STL preview GIF (generated on demand, cached)
  /api/comms/status  JSON {unlocked, configured}
  /api/otp/request   POST — generate one-time code, DM it via Discord, never echo it
  /api/otp/verify    POST {code} — unlock chat, set HttpOnly session cookie
  /api/comms/lock    POST — revoke session, clear cookie
  /api/chat          POST {message} — stream a Spock reply (SSE), requires session
  /camera      live MJPEG proxy (only serves frames while actively printing)
  /camera/snap single JPEG snapshot
"""
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = os.environ.get("3DPRINTER_STATE", "state.json")
PORT = int(os.environ.get("PORT", "8890"))
# Bind 0.0.0.0 so Docker port mappings work; restrict externally with a
# 127.0.0.1 host mapping or BIND=127.0.0.1 for bare-Python local use.
BIND = os.environ.get("BIND", "0.0.0.0")

# ---- COMMS (Spock chat bridge) ------------------------------------------
COMMS_LOCK = threading.Lock()
COMMS = {"otp": None, "sessions": {}}  # otp: {hash,expires,attempts,sent_at}

OTP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
OTP_TTL = int(os.environ.get("OTP_TTL", "600"))
SESSION_TTL = int(os.environ.get("SESSION_TTL", "86400"))
OTP_MIN_INTERVAL = int(os.environ.get("OTP_MIN_INTERVAL", "20"))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))
API_SERVER_URL = os.environ.get(
    "API_SERVER_URL", "http://host.docker.internal:8642/v1").rstrip("/")
API_SERVER_KEY = os.environ.get("API_SERVER_KEY", "")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_USER_ID = os.environ.get("DISCORD_USER_ID", "")

# ---- Replicator preview (rotating STL GIF) ------------------------------
PREVIEW_MODELS_DIR = os.environ.get("PREVIEW_MODELS_DIR", "models")
PREVIEW_CACHE_DIR = os.environ.get("PREVIEW_CACHE_DIR", "preview_cache")
PREVIEW_SIZE = int(os.environ.get("PREVIEW_SIZE", "320"))
PREVIEW_FRAMES = int(os.environ.get("PREVIEW_FRAMES", "24"))
PREVIEW_FPS = int(os.environ.get("PREVIEW_FPS", "12"))
PREVIEW_TILT = float(os.environ.get("PREVIEW_TILT", "28"))
_PREVIEW_GEN_LOCKS = {}
_PREVIEW_GEN_LOCKS_GUARD = threading.Lock()


def _model_index():
    """{stem: abs path} for every STL under PREVIEW_MODELS_DIR (recursive)."""
    idx = {}
    base = os.path.abspath(PREVIEW_MODELS_DIR)
    if not os.path.isdir(base):
        return idx
    for root, _dirs, files in os.walk(base):
        for fn in files:
            if fn.lower().endswith(".stl"):
                stem = os.path.splitext(fn)[0]
                idx.setdefault(stem, os.path.join(root, fn))
    return idx


def resolve_preview(gcode_name):
    """Match a printer gcode name to a local STL.

    Returns {"key": cache-key/stem, "name": display name, "path": stl} or
    None. Progressive suffix stripping handles slice.py naming like
    ``mani_dock_max_PLA.gcode`` -> ``mani_dock_max.stl`` and directory
    matches like ``wave_drip`` -> ``wave_drip/spoonge_holder.stl``.
    """
    stem = gcode_name.rsplit(".", 1)[0].strip()
    if not stem:
        return None
    idx = _model_index()
    if stem in idx:
        return {"key": stem, "name": stem, "path": idx[stem]}
    parts = stem.split("_")
    for i in range(len(parts) - 1, 0, -1):
        cand = "_".join(parts[:i])
        if cand in idx:
            return {"key": cand, "name": stem, "path": idx[cand]}
        d = os.path.join(os.path.abspath(PREVIEW_MODELS_DIR), cand)
        if os.path.isdir(d):
            inner = sorted(f for f in os.listdir(d) if f.lower().endswith(".stl"))
            if inner:
                k = os.path.splitext(inner[0])[0]
                return {"key": k, "name": stem,
                        "path": os.path.join(d, inner[0])}
    return None


def preview_gif(stem, stl_path):
    """Generate (or fetch cached) preview GIF for a model. Returns abs path."""
    os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)
    cache = os.path.join(PREVIEW_CACHE_DIR, stem + ".gif")
    if os.path.exists(cache):
        return cache
    with _PREVIEW_GEN_LOCKS_GUARD:
        lock = _PREVIEW_GEN_LOCKS.setdefault(stem, threading.Lock())
    with lock:
        if os.path.exists(cache):
            return cache
        import preview
        tris = preview.load_stl(stl_path)
        preview.make_gif(tris, cache, size=PREVIEW_SIZE,
                         frames=PREVIEW_FRAMES, fps=PREVIEW_FPS,
                         tilt=PREVIEW_TILT)
    return cache


def _now():
    return time.time()


def _gen_otp():
    """12-char code, 3 groups of 4, unambiguous alphabet."""
    return "-".join(
        "".join(secrets.choice(OTP_ALPHABET) for _ in range(4)) for _ in range(3))


def _discord_dm(user_id, content):
    """Open (or reuse) a DM channel with the bot token and send a message."""
    token = DISCORD_BOT_TOKEN
    if not token or not user_id:
        raise RuntimeError("DISCORD_BOT_TOKEN / DISCORD_USER_ID not set")
    headers = {"Authorization": f"Bot {token}",
               "Content-Type": "application/json",
               "User-Agent": "DiscordBot (lcars-printer, 1.0)"}
    req = urllib.request.Request(
        "https://discord.com/api/v10/users/@me/channels",
        data=json.dumps({"recipient_id": user_id}).encode(),
        headers=headers,
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        channel = json.loads(r.read().decode())
    req2 = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel['id']}/messages",
        data=json.dumps({"content": content}).encode(),
        headers=headers,
        method="POST")
    with urllib.request.urlopen(req2, timeout=15) as r:
        return json.loads(r.read().decode())


def _printer_target():
    """Return (host, serial, check_code) from env or the state file."""
    host = serial = code = None
    if os.path.exists(STATE):
        try:
            with open(STATE) as fh:
                st = json.load(fh)
            host = st["printer"]["host"]
            serial = st["printer"]["serial"]
            code = st["printer"]["check_code"]
        except Exception:
            pass
    host = os.environ.get("PRINTER_HOST", host)
    serial = os.environ.get("PRINTER_SERIAL", serial)
    code = os.environ.get("PRINTER_CHECK_CODE", code)
    if not (host and serial and code):
        raise RuntimeError(
            "printer credentials missing — set PRINTER_HOST/PRINTER_SERIAL/"
            "PRINTER_CHECK_CODE env vars or provide a state file")
    return host, serial, code


def _cam_urls():
    host, _, _ = _printer_target()
    return (f"http://{host}:8080/?action=stream",
            f"http://{host}:8080/?action=snapshot")


def _temp(t):
    if t is None:
        return None
    try:
        return {"current": round(float(t.current), 1), "set": round(float(t.set), 1)}
    except Exception:
        return None


def _status_payload(s):
    return {
        "machine_state": str(getattr(s, "machine_state", "")),
        "status": getattr(s, "status", ""),
        "file": getattr(s, "print_file_name", ""),
        "layer": getattr(s, "current_print_layer", 0),
        "total_layers": getattr(s, "total_print_layers", 0),
        "progress": getattr(s, "print_progress_int", 0),
        "eta": getattr(s, "print_eta", ""),
        "extruder": _temp(getattr(s, "extruder", None)),
        "bed": _temp(getattr(s, "print_bed", None)),
        "firmware": getattr(s, "firmware_version", ""),
        "ip": getattr(s, "ip_address", ""),
        "error": getattr(s, "error_code", ""),
    }


def _printer_snapshot():
    """One full query round-trip: status (HTTP) + file list (TCP)."""
    from flashforge import FlashForgeClient
    host, serial, code = _printer_target()

    async def _go():
        c = FlashForgeClient(host, serial, code)
        try:
            await c.init_control()
            s = await c.get_printer_status()
            fl = await c.files.get_file_list() or []
            return {"ok": True, "status": _status_payload(s),
                    "file_count": len(fl), "files": [str(f) for f in fl[-12:]]}
        finally:
            await c.dispose()

    try:
        return asyncio.run(asyncio.wait_for(_go(), timeout=25))
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # quiet

    def _send(self, code, body, ctype, cache=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control",
                         "public, max-age=86400" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _serve_file(self, name, ctype):
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   name), "rb") as fh:
                self._send(200, fh.read(), ctype)
        except OSError:
            self._send(404, f"{name} missing".encode(), "text/plain")

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    # ---- comms helpers ----
    def _comms_session(self):
        """Return the session token if the request carries a live cookie."""
        tok = None
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "lcars_comms":
                tok = v
                break
        if not tok:
            return None
        with COMMS_LOCK:
            s = COMMS["sessions"].get(tok)
            if not s:
                return None
            if _now() > s["expires"]:
                COMMS["sessions"].pop(tok, None)
                return None
        return tok

    def _otp_request(self):
        with COMMS_LOCK:
            now = _now()
            cur = COMMS["otp"]
            if cur and (now - cur["sent_at"]) < OTP_MIN_INTERVAL:
                self._json({"ok": False, "error": "rate_limited"}, 429)
                return
            code = _gen_otp()
            COMMS["otp"] = {"hash": hashlib.sha256(code.encode()).hexdigest(),
                            "expires": now + OTP_TTL,
                            "attempts": 0, "sent_at": now}
        try:
            _discord_dm(
                DISCORD_USER_ID,
                "🖖 **COMMS UNLOCK** — one-time code for the printer dashboard:\n\n"
                f"**{code}**\n\n"
                f"Valid {int(OTP_TTL / 60)} minutes · single use · "
                "sent only to this DM, never repeated in any other channel.")
        except Exception as e:
            with COMMS_LOCK:
                COMMS["otp"] = None
            self._json({"ok": False, "error": "discord_dm_failed",
                        "detail": str(e)[:120]}, 502)
            return
        # The code itself is never echoed in any response or log.
        self._json({"ok": True, "expires_in": OTP_TTL})

    def _otp_verify(self):
        body = self._read_json()
        code = str(body.get("code") or "").strip().upper()
        with COMMS_LOCK:
            cur = COMMS["otp"]
            if not cur:
                self._json({"ok": False, "error": "no_code"}, 403)
                return
            if _now() > cur["expires"]:
                COMMS["otp"] = None
                self._json({"ok": False, "error": "expired"}, 403)
                return
            if cur["attempts"] >= OTP_MAX_ATTEMPTS:
                COMMS["otp"] = None
                self._json({"ok": False, "error": "locked"}, 403)
                return
            if not hmac.compare_digest(
                    hashlib.sha256(code.encode()).hexdigest(), cur["hash"]):
                cur["attempts"] += 1
                self._json({"ok": False, "error": "invalid"}, 403)
                return
            COMMS["otp"] = None
            token = secrets.token_urlsafe(32)
            COMMS["sessions"][token] = {"expires": _now() + SESSION_TTL}
        secure = ("Secure; " if self.headers.get("X-Forwarded-Proto",
                                                 "").lower() == "https" else "")
        cookie = (f"lcars_comms={token}; Path=/; HttpOnly; SameSite=Strict; "
                  f"Max-Age={SESSION_TTL}; {secure}").rstrip("; ")
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _comms_lock(self):
        tok = None
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "lcars_comms":
                tok = v
                break
        with COMMS_LOCK:
            if tok:
                COMMS["sessions"].pop(tok, None)
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie",
                         "lcars_comms=; Path=/; HttpOnly; SameSite=Strict; "
                         "Max-Age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _chat(self):
        if not self._comms_session():
            self._json({"ok": False, "error": "unauthorized"}, 401)
            return
        if not API_SERVER_KEY:
            self._json({"ok": False, "error": "bridge_unconfigured"}, 503)
            return
        body = self._read_json()
        msg = str(body.get("message") or "").strip()
        if not msg:
            self._json({"ok": False, "error": "empty"}, 400)
            return
        if len(msg) > 4000:
            self._json({"ok": False, "error": "too_long"}, 400)
            return
        self._proxy_hermes(msg)

    def _proxy_hermes(self, message):
        """Forward to the Hermes api_server and stream the SSE reply through."""
        url = API_SERVER_URL + "/chat/completions"
        payload = {
            "model": "hermes-agent",
            "messages": [{"role": "user", "content": message}],
            "stream": True,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {API_SERVER_KEY}",
                     "Content-Type": "application/json",
                     "X-Hermes-Session-Id": "lcars-dash"},
            method="POST")
        try:
            upstream = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            self._json({"ok": False, "error": f"upstream_{e.code}",
                        "detail": detail}, 502)
            return
        except Exception:
            self._json({"ok": False, "error": "bridge_unreachable"}, 502)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            while True:
                chunk = upstream.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            upstream.close()

    # ---- routes ----
    def do_GET(self):
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        if path == "/":
            self._serve_file("index.html", "text/html; charset=utf-8")
        elif path == "/comms":
            self._serve_file("comms.html", "text/html; charset=utf-8")
        elif path == "/comms.js":
            self._serve_file("comms.js", "application/javascript; charset=utf-8")
        elif path == "/api/comms/status":
            self._json({"ok": True,
                        "unlocked": bool(self._comms_session()),
                        "configured": bool(DISCORD_BOT_TOKEN and DISCORD_USER_ID
                                           and API_SERVER_KEY)})
        elif path == "/api/status":
            self._json(_printer_snapshot())
        elif path == "/api/files":
            snap = _printer_snapshot()
            if snap.get("ok"):
                self._json({"ok": True, "file_count": snap["file_count"],
                            "files": snap["files"]})
            else:
                self._json(snap)
        elif path == "/api/preview":
            self._api_preview(qs)
        elif path.startswith("/preview/"):
            self._serve_preview(path)
        elif path == "/camera":
            self._proxy_stream(_cam_urls()[0])
        elif path == "/camera/snap":
            self._proxy_snapshot()
        else:
            self._send(404, b"not found", "text/plain")

    def _api_preview(self, qs):
        fname = (qs.get("file") or [""])[0]
        res = resolve_preview(fname)
        if not res:
            self._json({"ok": False, "error": "no_model"}, 404)
            return
        self._json({"ok": True, "name": res["name"],
                    "gif": "/preview/" + res["key"] + ".gif"})

    def _serve_preview(self, path):
        key = path[len("/preview/"):]
        if not key.endswith(".gif"):
            self._send(404, b"not found", "text/plain")
            return
        stem = key[:-4]
        stl = _model_index().get(stem)
        if not stl:
            self._send(404, b"no model", "text/plain")
            return
        try:
            gif = preview_gif(stem, stl)
            with open(gif, "rb") as fh:
                data = fh.read()
            self._send(200, data, "image/gif", cache=True)
        except Exception as e:
            self._send(500, str(e).encode()[:200], "text/plain")

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/otp/request":
            self._otp_request()
        elif path == "/api/otp/verify":
            self._otp_verify()
        elif path == "/api/comms/lock":
            self._comms_lock()
        elif path == "/api/chat":
            self._chat()
        else:
            self._send(404, b"not found", "text/plain")

    def _proxy_snapshot(self):
        try:
            with urllib.request.urlopen(urllib.request.Request(_cam_urls()[1]),
                                        timeout=15) as r:
                data = r.read()
            self._send(200, data, r.headers.get("Content-Type", "image/jpeg"))
        except Exception as e:
            self._send(502, str(e).encode()[:200], "text/plain")

    def _proxy_stream(self, url):
        """Stream the printer's MJPEG through to the browser."""
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
                self.send_response(200)
                self.send_header("Content-Type", r.headers.get(
                    "Content-Type", "multipart/x-mixed-replace; boundary=frame"))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            try:
                self._send(502, b"camera unavailable", "text/plain")
            except Exception:
                pass


def main():
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print(f"lcars-printer listening on {BIND}:{PORT}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
