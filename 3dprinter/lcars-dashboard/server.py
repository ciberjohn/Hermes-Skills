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

NOTE: the AD5X only serves its local HTTP API (port 8898) when the printer is
in LAN-only mode (touchscreen: Settings -> WiFi -> Network Mode -> Local
Network Only). The camera stream (8080) only serves frames while actively
printing.

Endpoints:
  /            LCARS dashboard (index.html)
  /api/status  JSON printer status (state, temps, layer, progress, ETA)
  /api/files   JSON last files on the printer
  /camera      live MJPEG proxy (only serves frames while actively printing)
  /camera/snap single JPEG snapshot
"""
import asyncio
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = os.environ.get("3DPRINTER_STATE", "state.json")
PORT = int(os.environ.get("PORT", "8890"))
# Bind 0.0.0.0 so Docker port mappings work; restrict externally with a
# 127.0.0.1 host mapping or BIND=127.0.0.1 for bare-Python local use.
BIND = os.environ.get("BIND", "0.0.0.0")


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

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            try:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "index.html"), "rb") as fh:
                    self._send(200, fh.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, b"index.html missing", "text/plain")
        elif path == "/api/status":
            self._json(_printer_snapshot())
        elif path == "/api/files":
            snap = _printer_snapshot()
            if snap.get("ok"):
                self._json({"ok": True, "file_count": snap["file_count"],
                            "files": snap["files"]})
            else:
                self._json(snap)
        elif path == "/camera":
            self._proxy_stream(_cam_urls()[0])
        elif path == "/camera/snap":
            self._proxy_snapshot()
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
