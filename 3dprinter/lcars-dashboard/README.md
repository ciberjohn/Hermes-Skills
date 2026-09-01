# LCARS Printer Dashboard (FlashForge AD5X)

A Star Trek LCARS-styled micro dashboard for watching your FlashForge AD5X
printer: machine state, nozzle/bed thermals, layer/progress/ETA, on-board file
list, a live camera feed, and a **Replicator Preview** — an automatically
generated rotating STL GIF of the object currently printing — all served over
your tailnet.

**One codebase, three deployments.** The same env-driven code runs on:

| Flavor | Where | `.env` PRINTER_HOST | Exposed via |
|---|---|---|---|
| João's machine | home PC, same LAN as printer | printer LAN IP (`192.168.40.126`) | LAN or tailnet |
| VPS (Spock) | VPS, remote | relay/tailnet host forwarding 8898/8899/8080 | `tailscale serve` |
| Generic / public | anywhere | either of the above | your choice |

The only difference between deployments is the `.env` file — the "magic sauce"
(serial number, check code, addresses) never lives in this repo.

## Requirements

- FlashForge AD5X in **LAN-only mode** (Settings → WiFi → Network Mode →
  Local Network Only). The printer only serves its local HTTP API (8898) in
  LAN mode — see the parent skill's SKILL.md for the full saga.
- Docker (for the container route) — or Python 3.11 + `flashforge-python-api`.
- Replicator Preview additionally needs **numpy + Pillow** (already in the
  Docker image; `pip install numpy pillow` for bare-Python runs) and a folder
  of STL files — the compose file mounts `./models` read-only. The dashboard
  matches the printer's gcode name (e.g. `mani_dock_max_PLA.gcode`) to a local
  STL (`mani_dock_max.stl`) by progressive suffix stripping, so keep the model
  files that you sliced.

## Quick start (Docker)

```bash
cp .env.example .env      # fill in your printer's values
docker compose up -d --build
# dashboard now on http://127.0.0.1:8890
```

## Expose over Tailscale (tailnet-only — NOT funnel)

```bash
tailscale serve --bg 8890
# https://<your-node>.<tailnet>.ts.net  → 127.0.0.1:8890
```

`tailscale serve` keeps the site **private to your tailnet** (unlike
`tailscale funnel`, which publishes to the internet — don't use funnel here:
the printer API has no auth beyond the check code).

## Quick start (bare Python)

```bash
pip install flashforge-python-api==1.4.0
export PRINTER_HOST=192.168.40.126 PRINTER_SERIAL=... PRINTER_CHECK_CODE=...
python server.py
```

## Watch gate (by design)

The dashboard does **not** poll or stream until you press **▶ ENGAGE WATCH**;
**■ STAND DOWN** closes the feed, and switching tabs auto-pauses polling and
the camera. The printer's network stack is weak — don't hammer it.

## Endpoints

| Path | What |
|---|---|
| `/` | LCARS dashboard (index.html) |
| `/api/status` | JSON status: state, temps, layer, progress, ETA, firmware, IP |
| `/api/files` | JSON last files on the printer |
| `/api/preview?file=<gcode>` | JSON `{ok, name, gif}` — resolve a printing gcode name to a local STL and report its preview GIF URL |
| `/preview/<stem>.gif` | rotating STL preview GIF (generated on demand, cached under `preview_cache/`) |
| `/api/comms/status` | JSON `{unlocked, configured}` |
| `/api/otp/request` | POST — generate one-time unlock code, DM it via Discord, never echo it |
| `/api/otp/verify` | POST `{code}` — unlock chat, set HttpOnly session cookie |
| `/api/comms/lock` | POST — revoke session, clear cookie |
| `/api/chat` | POST `{message}` — stream a Spock reply (SSE), requires session |
| `/camera` | live MJPEG proxy (only serves frames while actively printing) |
| `/camera/snap` | single JPEG snapshot |

## Replicator Preview

While a print is running, the dashboard shows a rotating LCARS-styled preview
of the object — orange shaded solid on a dark teal build plate, generated from
the source STL (36-frame rotation, ~300–500 KB GIF):

- First request for a model renders the GIF on demand (a few seconds for big
  meshes, <1 s for small ones); every later request is a disk-cache hit.
- No STL match → the panel reports **NO MODEL ON FILE** (the printer only
  reports the gcode name; if you sliced elsewhere, drop the STL into
  `./models`).
- The renderer is `preview.py` — pure numpy + Pillow (no OpenGL): binary/ASCII
  STL reader, perspective camera, painter's algorithm, near-plane clipping.
  Use it standalone: `python3 preview.py model.stl out.gif`.

## Comms bridge (optional)

The 🖖 **COMMS** panel lets you chat with your Hermes agent straight from the
dashboard. It is locked by default: requesting a code DMs a one-time code to
your Discord, and the session is an HttpOnly cookie. All credentials are env
vars (`DISCORD_BOT_TOKEN`, `DISCORD_USER_ID`, `API_SERVER_URL`,
`API_SERVER_KEY`) — nothing hardcoded, nothing in this repo.

## Notes & pitfalls

- The camera stream only serves frames while the printer is **actively
  printing**; it's silent while paused/feeding (firmware behavior).
- The printer's touchscreen freeze and HTTP-API drops are the same wedged
  process on the stock firmware — LAN-only mode + gentle polling (the watch
  gate) are the practical mitigations.
- **Comms bridge routing gotcha:** if the COMMS panel shows "agent unreachable
  — is the gateway up?", the usual cause is Docker routing:
  `host.docker.internal` resolves to the **docker0** gateway (172.17.0.1), NOT
  your compose network's gateway, so a gateway API bound to the
  compose-network gateway IP is unreachable. Fix: set `API_SERVER_URL` to the
  container network's literal gateway IP, and/or bind the gateway API on
  `0.0.0.0` (authenticated with the API key).
- The parent skill (`3dprinter`) documents the full printer setup: channel
  inventory, slicing (slice.py), purge routine, PLA+/raft lessons, and the
  LAN-mode root cause.
