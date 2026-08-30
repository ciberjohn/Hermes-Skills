---
name: 3dprinter
description: "Use when slicing STL/3MF to print on a Flashforge AD5X, or asking about the printer. Headless OrcaSlicer + FlashForge LAN API."
license: MIT
metadata:
  version: "1.0.0"
  tags: [3d-printing, orcaslicer, flashforge, ad5x, stl, gcode]
  platforms: [linux]
  related_skills: []
---

# 3dprinter — Flashforge AD5X print pipeline

Headless slicing + printing for a **Flashforge AD5X** (220³ mm, 1 toolhead,
4-channel material station) using OrcaSlicer in CLI mode and the
`flashforge-python-api` library over the printer's LAN API.

## Configuration Variables

Set these before running the pipeline, or answer the install prompt and let your agent configure them:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `{{PRINTER_IP}}` | Yes | LAN IP of the printer | `192.168.10.50` |
| `{{PRINTER_SERIAL}}` | Yes | Serial number (Settings → About on the printer) | `SNXXXXXXXXXXXX` |
| `{{PRINTER_CHECK_CODE}}` | Yes | Check code / Printer ID (Settings → Network) | `a1b2c3d4` |
| `{{ORCA_BIN}}` | Yes | Path to OrcaSlicer (AppImage or extracted binary) | `~/OrcaSlicer.AppImage` |
| `{{ORCA_DATADIR}}` | No | OrcaSlicer config datadir (default: OrcaSlicer default) | `~/orca-data` |
| `{{ORCA_MACHINE_PROFILE}}` | Yes | Path to the `Flashforge AD5X 0.4 nozzle` machine profile JSON | `~/OrcaSlicer/profiles/Flashforge AD5X 0.4 nozzle.json` |
| `{{STATE_FILE}}` | No | State JSON (default `~/3dprinter/state.json`; override with `3DPRINTER_STATE`) | `~/3dprinter/state.json` |

## Trigger conditions

1. User sends an **STL / 3MF / OBJ** file → run the slice workflow.
2. User asks "can you print X?" or references a model → same workflow.
3. User asks about printer status, material station, or what's loaded → status/channels.

## Setup

1. Install **OrcaSlicer** (Linux AppImage works headless; the AppImage needs
   `libopengl0 libglu1-mesa libwebkit2gtk-4.1-0` on Debian/Ubuntu).
2. Install the Python API: `pip install flashforge-python-api`.
3. Copy `assets/profiles/*.json` (SOP-tuned PLA/PETG filament profiles and a
   quality process profile) next to your OrcaSlicer profile collection, and
   point `{{ORCA_MACHINE_PROFILE}}` at the "Flashforge AD5X 0.4 nozzle" machine
   profile that ships with OrcaSlicer.
4. Create `{{STATE_FILE}}` (default `~/3dprinter/state.json`; override with the
   `3DPRINTER_STATE` env var). The variables map into it like this:
   - `{{PRINTER_IP}}`, `{{PRINTER_SERIAL}}`, `{{PRINTER_CHECK_CODE}}` →
     `printer.host` / `printer.serial` / `printer.check_code`
   - `{{ORCA_BIN}}`, `{{ORCA_DATADIR}}`, `{{ORCA_MACHINE_PROFILE}}` →
     `slicer.orca_bin` / `slicer.datadir` / `slicer.machine_profile`
   - `{{STATE_FILE}}` → the file itself (or `3DPRINTER_STATE`)

   Then `chmod 600 {{STATE_FILE}}` — it holds printer credentials
   (serial + check code). The channels.py script enforces 0600 on writes.
   Full example:
   ```json
   {
     "printer": {"host": "192.168.10.50", "serial": "SNXXXXXXXXXXXX", "check_code": "a1b2c3d4", "model": "Flashforge AD5X"},
     "channels": {"1": {"material": null, "color": null, "brand": null, "remaining_pct": null}, "2": {"material": null, "color": null, "brand": null, "remaining_pct": null}, "3": {"material": null, "color": null, "brand": null, "remaining_pct": null}, "4": {"material": null, "color": null, "brand": null, "remaining_pct": null}},
     "slicer": {"orca_bin": "~/OrcaSlicer.AppImage", "datadir": "~/orca-data", "machine_profile": "~/OrcaSlicer/profiles/Flashforge AD5X 0.4 nozzle.json", "profiles_dir": "~/profiles", "output_dir": "~/gcode"},
     "defaults": {"layer_height": 0.2, "infill_percent": 15, "supports": "auto", "auto_start_print": false}
   }
   ```

## Slice workflow

1. **Receive model** — save the attachment to a local models directory.
2. **Ask channels** — confirm the material station before slicing: which
   channel(s), material, and color are loaded (`channels.py show` first;
   confirm changes with the user; do not assume the state file is current).
3. **Ask print intent** — purpose drives parameters (see policy below):
   decorative / functional / prototype; supports on/off; quantity.
4. **Slice**:
   ```bash
   python3 scripts/slice.py model.stl --material PLA [--name foo]
   ```
   → gcode at `<output_dir>/<name>_<MATERIAL>.gcode` plus est. time, layers and
   `bed_verified` (the script fixes the OrcaSlicer bed-temp quirk and verifies).
5. **Report** — est time, material, layer count; ask **confirm to upload/print**
   (default: upload + confirm before starting; bed must be clear, filament loaded).
6. **Upload/start**:
   ```bash
   python3 scripts/ff_print.py upload <gcode> [--start]
   python3 scripts/ff_print.py status
   ```

## Parameter policy (agent-owned)

Pick optimal values for **quality/speed balance + easy support removal**.
Defaults (0.4 mm nozzle, AD5X):

| Parameter | Default | Decorative | Functional |
|---|---|---|---|
| Layer height | 0.20 mm | 0.24 mm | 0.16–0.20 mm |
| Infill | 15% gyroid | 10–12% | 20–25% (gyroid/cubic) |
| Walls (loops) | 3 | 2 | 4+ |
| Top/bottom shells | 5 / 4 | 4 / 3 | 6 / 5 |
| Supports | tree(auto), slim | tree slim | tree strong |
| Support z-gap | top 0.24 / bottom 0.20 | — | top 0.2 |
| Support interface | disabled (snap-off) | — | sparse |

- Supports: **tree by default**, interface disabled for clean snap-off; switch
  to `none` when the model self-supports or geometry is simple.
- Brim: auto; skirt only when a raft is needed (rare on PEI).

## Material table (recommended starting points)

| | PLA | PETG |
|---|---|---|
| Nozzle | 210°C (range 205–215) | 240°C (range 235–245) |
| Bed | 62°C (initial 65) | 80°C |
| Retraction | 0.9 mm @ 45 mm/s | 1.3 mm @ 40 mm/s |
| Fan | 100% | 20–35% |
| Flow ratio | 1.00 (0.98–1.02) | 0.96 (0.95–0.97) |
| Bed prep | No glue; clean with dish soap | **Glue stick mandatory** (PETG fuses to PEI); let bed cool before removal |
| Wet filament | — | "popping"/stringing → dry 65°C / 6 h |

## Scripts

- `scripts/slice.py` — headless slice + bed-temp fix + verification
- `scripts/ff_print.py` — status / list / upload / cancel via flashforge-python-api
- `scripts/channels.py` — material station inventory (show / set / clear)

All scripts read the state file from `{{STATE_FILE}}` (or `$3DPRINTER_STATE`).

## Pitfalls

- **OrcaSlicer 2.4.2 AD5X bed-temp quirk**: filament `bed_temperature*` keys can
  be ignored on this machine (gcode emits `M190/M140 S35`). `slice.py`
  post-processes bed temps from the material table and verifies — never ship
  gcode with a 35°C bed. Verify: `grep -oE "M1(90|40) S[0-9]+" file.gcode`.
- **HTTP API (8898) requires LAN mode**: if all HTTP requests get empty replies
  while TCP 8899 works, the printer is not in **LAN mode** (touchscreen
  Settings → Network) — enable it and reboot. LAN mode disables the vendor
  cloud app's webcam monitoring; use the printer's own MJPEG stream instead:
  `http://<PRINTER_IP>:8080/?action=stream` (also returned by `POST /detail`
  as `cameraStreamUrl`; the library exposes it via
  `client.info.get_detail_response()` → `.camera_stream_url`). Open the URL in
  any browser to watch the print.
- **AD5X material-station uploads**: for multi-color/material-station prints
  use `upload_file_ad5x` with `AD5XUploadParams` (+ material mappings); the
  `ff_print.py` `upload` command uses the simpler `upload_file` path (fine for
  single-material jobs).
- **Credentials**: serial number + check code are per-printer credentials —
  keep them out of logs, bug reports, and public repos; `chmod 600` the state
  file (channels.py enforces it on writes).
- **Never start a print without confirming** the bed is clear and the right
  channel/material is loaded. `defaults.auto_start_print` is an agent-level
  policy (the agent reads it and refuses to auto-start when false); the CLI
  `--start` flag is the explicit override after confirmation.

## Verification

- Slice test: `slice.py test_cube.stl --material PLA --json` → `bed_verified: true`,
  temps `M190 S65` / `M140 S62`, nozzle 210/215.
- Printer: `ff_print.py status` → file count (TCP fallback works even when HTTP is down).
