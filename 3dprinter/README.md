# 3dprinter

A **Hermes Agent** skill that turns a Flashforge AD5X into a print pipeline the
agent can drive from chat: drop an STL, confirm what's loaded in the 4-channel
material station, and get a sliced, verified gcode — with upload/print via the
printer's LAN API.

## What It Does

- **SLICE** — headless OrcaSlicer 2.4.2 CLI slicing with SOP-tuned filament
  profiles (PLA/PETG) and a quality process profile. The agent picks optimal
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

## Quick Install

Copy and paste this to your Hermes agent (it will install into your active profile's skills directory):

```text
Install the 3dprinter skill from https://github.com/ciberjohn/Hermes-Skills.
Copy 3dprinter/SKILL.md into ~/.hermes/skills/3dprinting/3dprinter/SKILL.md,
the contents of 3dprinter/scripts/ into .../scripts/, the contents of
3dprinter/assets/ into .../assets/, and 3dprinter/.gitignore into .../.gitignore.
Create the subdirectories if they don't exist. Then:
1. Copy 3dprinter/assets/profiles/*.json into ~/3dprinter/profiles/.
2. Ask me:
   1. What is the LAN IP of the Flashforge AD5X printer?
   2. What is the printer's serial number?
   3. What is the printer's check code / Printer ID (Settings -> Network)?
   4. Where is OrcaSlicer installed (path to the AppImage or binary)?
   5. Where is the 'Flashforge AD5X 0.4 nozzle' machine profile JSON?
3. Create ~/3dprinter/state.json with my answers, setting slicer.profiles_dir
   to ~/3dprinter/profiles/ and slicer.output_dir to ~/3dprinter/gcode.
4. chmod 600 ~/3dprinter/state.json (it holds printer credentials).
5. Install flashforge-python-api, then verify with a test slice of a 20mm cube
   and show me the output.
```

## Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com) — the skill engine.
- **OrcaSlicer** (2.4.x) on a Linux host — AppImage works headless. Debian/Ubuntu
  runtime deps: `libopengl0 libglu1-mesa libwebkit2gtk-4.1-0`.
- **Python 3** + `pip install flashforge-python-api` for the printer-control script.
- **Flashforge AD5X** with LAN mode enabled; serial number and check code
  (Printer ID) from the printer's touchscreen (Settings → Network).

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
