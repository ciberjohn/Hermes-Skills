# openscad-cad

A **Hermes Agent** skill for the DESIGN stage of 3D printing: turn a sketch,
annotated photo, or spoken description with dimensions into a parametric
OpenSCAD model, render it to a verified binary STL — then hand off to the
sibling `3dprinter` skill for slicing and printing.

## What It Does

- **MODEL** — encodes your sketch/dimensions as parametric OpenSCAD (named
  dimension variables, one module per feature, printability `assert()`s).
- **RENDER** — headless CLI export to binary STL (`openscad -o out.stl
  --export-format binstl part.scad`), with `-D 'var=value'` overrides so an
  agent can iterate dimensions without editing the source file.
- **VERIFY** — manifoldness from OpenSCAD's `Simple: yes` render report,
  binary-STL well-formedness check, bed-envelope check, and preview PNGs via
  the sibling `3dprinter` skill's `stl_preview.py`.
- **HAND OFF** — hands the STL to the `3dprinter` skill (headless OrcaSlicer
  → Flashforge AD5X), so "design me a bracket" and "print this STL" become
  one continuous chat flow.

## Quick Install

Copy and paste this to your Hermes agent (it will install into your active profile's skills directory):

```text
Install the openscad-cad skill from https://github.com/ciberjohn/Hermes-Skills.
Copy openscad-cad/SKILL.md into ~/.hermes/skills/3dprinting/openscad-cad/SKILL.md
and the contents of openscad-cad/templates/ into .../templates/.
Create the subdirectories if they don't exist. Then:
1. Install OpenSCAD (Debian/Ubuntu: sudo apt-get install -y openscad) and
   verify with `openscad --version`.
2. Optionally install the sibling 3dprinter skill so designed STLs can be
   sliced and printed; its scripts/stl_preview.py provides preview PNGs.
3. Ask me to run a smoke test: render the bundled template
   (templates/parametric-part.scad) and show you the resulting STL preview.
```

## Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com) — the skill engine.
- **OpenSCAD** on a Linux host (Debian/Ubuntu: `sudo apt-get install -y openscad`; other platforms: https://openscad.org/downloads.html).
- Optional: the sibling `3dprinter` skill for slicing/printing the result.

## How to Use

1. Tell the agent what you want: send a photo of a hand sketch, describe the
   part, or say "design X with these dimensions: …".
2. The agent confirms units (mm vs cm) and critical-fit dimensions, then
   builds a parametric `.scad` from `templates/parametric-part.scad`.
3. It renders the STL and verifies: manifold (`Simple: yes`), well-formed
   binary STL, bed-envelope fit, and preview images.
4. Iterate in plain language — "make it 4 mm wider" — until it looks right.
5. Hand off to `3dprinter` for slicing and printing.

Example:

```bash
openscad -o bracket.stl -D 'width=44' -D 'depth=28' -D 'hole_d=5.5' --export-format binstl bracket.scad
```

## Expected Directory Structure

```
openscad-cad/
├── SKILL.md                 # Skill instructions (this skill)
├── README.md                # This file
├── .gitignore
└── templates/
    └── parametric-part.scad # Starter: named dims, asserts, printable defaults
```

## FDM Design Constraints Cheat-Sheet

For a 0.4 mm nozzle: walls ≥ 0.8 mm (2 perimeters), features/text ≥ 1.2 mm
relief, through-holes ≥ 1.2 mm Ø, sliding fits +0.3–0.4 mm clearance, overhangs
≤ 45° unsupported, and keep parts ≤ 210³ mm on a 220 mm bed. Full table in
`SKILL.md`.

## License

MIT. PRs welcome via the [Hermes-Skills repo](https://github.com/ciberjohn/Hermes-Skills).
