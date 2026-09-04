# 3dprinter

A **Hermes Agent** skill that turns a Flashforge AD5X into a print pipeline the
agent can drive from chat: drop an STL, confirm what's loaded in the 4-channel
material station, and get a sliced, verified gcode — with upload/print via the
printer's LAN API.

## What It Does

- **SLICE** — headless OrcaSlicer 2.4.2 CLI slicing with SOP-tuned filament
  profiles (PLA/PETG) plus quality and fast process profiles. The agent picks optimal
  infill/support parameters per print intent (quality/speed balance + easy
  support removal).
- **VERIFY** — the slice script fixes a known OrcaSlicer bed-temp quirk on the
  AD5X (filament bed keys ignored → 35°C) and verifies the gcode temps before
  anything ships.
- **PRINT** — `flashforge-python-api` for status, file list, upload, and job
  control over the printer's LAN HTTP/TCP API.
- **CHANNELS** — material station inventory (4 slots: material/color/brand/
  remaining) kept in a state file; the agent confirms the current loadout at
  print time instead of assuming.
- **DESIGN FIRST?** — want a part modeled, not just an existing STL sliced?
  Sibling skill [`openscad-cad`](../openscad-cad/) turns a sketch / photo /
  spoken dimensions into a parametric STL (OpenSCAD), then this skill takes
  over for slicing and printing.

## Quick Install

Copy and paste this to your Hermes agent (it will install into your active profile's skills directory):

```text
Install the 3dprinter skill from https://github.com/ciberjohn/Hermes-Skills.
Copy 3dprinter/SKILL.md into ~/.hermes/skills/3dprinting/3dprinter/SKILL.md,
the contents of 3dprinter/scripts/ into .../scripts/, the contents of
3dprinter/assets/ into .../assets/, and 3dprinter/.gitignore into .../.gitignore.
Create the subdirectories if they don't exist. Then:
1. If OrcaSlicer isn't installed yet, install it (see "Installing OrcaSlicer"
   in the README — download the AppImage, apt-get the 4 runtime deps, chmod +x).
2. Copy 3dprinter/assets/profiles/*.json into ~/3dprinter/profiles/.
3. Ask me:
   1. What is the LAN IP of the Flashforge AD5X printer?
   2. What is the printer's serial number?
   3. What is the printer's check code / Printer ID (Settings -> Network)?
   4. Where is OrcaSlicer installed (path to the AppImage or binary)?
   5. Where is the 'Flashforge AD5X 0.4 nozzle' machine profile JSON?
4. Create ~/3dprinter/state.json with my answers, setting slicer.profiles_dir
   to ~/3dprinter/profiles/ and slicer.output_dir to ~/3dprinter/gcode.
5. chmod 600 ~/3dprinter/state.json (it holds printer credentials).
6. Install flashforge-python-api, then verify with a test slice of a 20mm cube
   and show me the output.
```

## Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com) — the skill engine.
- **OrcaSlicer** (2.4.x) on a Linux host — AppImage works headless. See
  [Installing OrcaSlicer](#installing-orcaslicer) below.
- **Python 3** + `pip install flashforge-python-api` for the printer-control script.
- **Flashforge AD5X** with LAN mode enabled; serial number and check code
  (Printer ID) from the printer's touchscreen (Settings → Network).

## Installing OrcaSlicer

The skill does **not** bundle OrcaSlicer — install it once on the host that
will slice (Linux; the AppImage runs headless):

```bash
# 1. Runtime deps (Debian/Ubuntu)
sudo apt-get install -y libopengl0 libglu1-mesa libwebkit2gtk-4.1-0 libjavascriptcoregtk-4.1-0

# 2. Download the Linux AppImage (v2.4.2, x86_64 Ubuntu 24.04)
curl -L -o ~/OrcaSlicer.AppImage \
  https://github.com/OrcaSlicer/OrcaSlicer/releases/download/v2.4.2/OrcaSlicer_Linux_AppImage_Ubuntu2404_V2.4.2.AppImage
chmod +x ~/OrcaSlicer.AppImage

# 3. Verify the CLI responds
~/OrcaSlicer.AppImage --help
```

Headless notes:

- If the AppImage refuses to run headless, either export
  `APPIMAGE_EXTRACT_AND_RUN=1` or extract it once and run the extracted binary:
  `~/OrcaSlicer.AppImage --appimage-extract` → `~/squashfs-root/AppRun`.
- Newer releases: https://github.com/OrcaSlicer/OrcaSlicer/releases (asset
  pattern `OrcaSlicer_Linux_AppImage_Ubuntu2404_*.AppImage`; pick the x86_64
  one unless your host is aarch64).
- Point `ORCA_BIN` / `slicer.orca_bin` at the AppImage (or the extracted
  `AppRun`).

## Installation

1. Place the skill directory inside your Hermes skills path:
   ```
   ~/.hermes/skills/3dprinting/3dprinter/
   ```
2. Create the state file (see the Quick Install prompt; the agent does this
   conversationally). Location defaults to `~/3dprinter/state.json`:
   ```json
   {
     "printer": {"host": "<LAN IP>", "serial": "<SN>", "check_code": "<Printer ID>", "model": "Flashforge AD5X"},
     "channels": {"1": {"material": null, "color": null, "brand": null, "remaining_pct": null}, "2": {"material": null, "color": null, "brand": null, "remaining_pct": null}, "3": {"material": null, "color": null, "brand": null, "remaining_pct": null}, "4": {"material": null, "color": null, "brand": null, "remaining_pct": null}},
     "slicer": {"orca_bin": "<path to OrcaSlicer>", "datadir": "<datadir or omit>", "machine_profile": "<path to 'Flashforge AD5X 0.4 nozzle' machine JSON>", "profiles_dir": "~/3dprinter/profiles", "output_dir": "~/3dprinter/gcode"},
     "defaults": {"layer_height": 0.2, "infill_percent": 15, "supports": "auto", "auto_start_print": false}
   }
   ```
   Then `chmod 600 ~/3dprinter/state.json` (the file holds the printer serial
   and check code; `channels.py` re-enforces 0600 on writes).
   Set `3DPRINTER_STATE` to use a different state file location.
3. Copy `assets/profiles/*.json` into `profiles_dir` (they inherit from the
   FlashForge Generic PLA/PETG and AD5X system profiles that ship with OrcaSlicer).

## Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `PRINTER_IP` | Yes | LAN IP of the printer | `192.168.10.50` |
| `PRINTER_SERIAL` | Yes | Serial number (Settings → About) | `SNXXXXXXXXXXXX` |
| `PRINTER_CHECK_CODE` | Yes | Check code / Printer ID (Settings → Network) | `a1b2c3d4` |
| `ORCA_BIN` | Yes | Path to OrcaSlicer | `~/OrcaSlicer.AppImage` |
| `ORCA_DATADIR` | No | OrcaSlicer datadir | `~/orca-data` |
| `ORCA_MACHINE_PROFILE` | Yes | AD5X 0.4 machine profile JSON | `~/OrcaSlicer/profiles/Flashforge AD5X 0.4 nozzle.json` |
| `STATE_FILE` | No | State JSON path (default `~/3dprinter/state.json`) | `~/3dprinter/state.json` |

## Expected Directory Structure

```
3dprinter/
├── SKILL.md                 # Skill instructions (this skill)
├── README.md                # This file
├── .gitignore
├── assets/
│   └── profiles/            # SOP-tuned OrcaSlicer profiles (PLA, PETG, process)
│       ├── Spock PLA @FF AD5X.json
│       ├── Spock PETG @FF AD5X.json
│       └── Spock Quality 0.20 @FF AD5X.json
└── scripts/
    ├── slice.py             # Headless slice + bed-temp fix + verification
    ├── ff_print.py          # Printer status / list / upload / cancel
    └── channels.py          # Material station inventory (show / set / clear)
```

## How to Use

1. Send the agent an STL (Discord, Signal, chat).
2. It confirms the material station loadout (which channel, what color/material)
   and the print intent.
3. It slices with `slice.py`, reports est. time + layers, and asks before
   uploading/starting.
4. `ff_print.py upload <gcode> [--start]` pushes and optionally starts the job.

## Output Files

| Artifact | Location | Notes |
|----------|----------|-------|
| gcode | `<output_dir>/<name>_<MATERIAL>.gcode` | Bed temps verified by `slice.py` |
| state | `STATE_FILE` | Printer + channels + defaults (JSON, chmod 600) |

## Customising

- **Material table**: edit `BED_TEMP` / the `assets/profiles/` JSONs to match
  your filaments (brand-specific temps, retraction).
- **Parameter policy**: the SKILL.md table drives what the agent picks; adjust
  the process profile JSON or the policy table to taste.
- **Multi-color**: the AD5X material station supports multi-color jobs via the
  API (`start_ad5x_multi_color_job`); the skill currently covers single-material
  prints.

## Contributing / License

MIT. PRs welcome via the [Hermes-Skills repo](https://github.com/ciberjohn/Hermes-Skills).
