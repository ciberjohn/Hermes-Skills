---
name: openscad-cad
description: "Use when designing a 3D-print object from sketch/dims."
license: MIT
metadata:
  version: "1.0.0"
  tags: [3d-printing, openscad, cad, parametric, stl, design]
  platforms: [linux]
  related_skills: [3dprinter, multipart-stl-plates, stl-mesh-rendering]
---

# openscad-cad — parametric design: sketch + dimensions → printable STL

The DESIGN stage of the print pipeline. Sibling skill `3dprinter` (same
3dprinting/ category) handles everything AFTER an STL exists (slice, verify,
upload, print on a Flashforge AD5X). This skill handles everything BEFORE:
turning a sketch, photo, or spoken description with dimensions into a
parametrically-coded, verified, printable STL.

## Trigger conditions

1. User says "design / make / create an object" (or "can you model X?") and
   supplies a sketch, annotated photo, or verbal dimensions.
2. User hands over a rough sketch / photo with arrows + measurements and
   expects a dimensional model back.
3. Iteration on an existing model: "make it 4 mm wider", "add a hole here".
4. A downloaded STL needs dimensioning edits (re-model it here instead of
   mesh-sculpting; then continue in `3dprinter` / `multipart-stl-plates`).

## Tooling

- **OpenSCAD** — code-driven parametric CAD: the model is text, dimensions are
  named variables, STL export is CLI-only. Ideal for agent-driven design
  (chat → .scad → STL), and every model is git-versionable. Install on
  Debian/Ubuntu:
  ```bash
  sudo apt-get install -y openscad   # universe repo; verify with `openscad --version`
  ```
  On other distros use the official binary from https://openscad.org/downloads.html.
- **CadQuery / build123d** (Python, OCCT kernel) — optional. Only reach for it
  when geometry is genuinely computed (threads, patterns, math-defined curves)
  and OpenSCAD becomes painful. `pip install cadquery` pulls ~1 GB of OCCT
  wheels — ask the user before installing.
- **Preview renders** — `stl_preview.py` from sibling skill `3dprinter`
  (scripts/) renders iso/front/side/top PNGs with no GPU deps.

## Workflow

### 1. Gather the spec (do not skip)

Ask until every dimension that affects printability is known. Default to a
markdown table of named dimensions so the user can correct one value and the
rest of the flow stays honest:

```markdown
| dim | value (mm) |
|-----|-----------|
| width | 40 |
| depth  | 25 |
| height | 12 |
| wall   | 2   |
| hole Ø | 5   |
```

When the user supplies a photo of a hand sketch, confirm units (cm vs mm is
the classic 10× disaster) and which measurements are critical fits.

### 2. Author the parametric model

Start from `templates/parametric-part.scad`. Rules:

- All dimensions as named variables at the top — never literals scattered in
  geometry. Iteration = edit variable + re-render.
- One module per logical feature; assemble in a top-level `union()`/`difference()`.
- `$fn = 64` for smooth curves; drop to 6–12 only for stylized/low-poly
  effects or when triangle count explodes (many holes).
- Add `assert()` statements for sanity bounds (e.g. wall ≥ 0.8 mm,
  overall ≤ bed envelope).
- Comments: one line per feature naming the dimension it uses.

### 3. Render to STL (CLI, headless)

```bash
openscad -o out.stl --export-format binstl part.scad
# Override a dimension from chat without editing the file:
openscad -o out.stl -D 'width=44' -D 'depth=28' --export-format binstl part.scad
```

Binary STL is the default format for slicers and for the `3dprinter` skill.
If exporting ASCII for diffing, add `--export-format asciistl`.

### 4. Verify before showing the user

- **Manifoldness**: OpenSCAD's stderr prints `Simple: yes/no` after rendering
  (CGAL). `Simple: no` means non-manifold — fix the CSG before slicing.
- **Well-formed file**: assert the binary size:
  ```python
  import struct
  d = open('out.stl','rb').read(); n = struct.unpack('<I', d[80:84])[0]
  assert len(d) == 84 + 50*n  # header(80) + count(4) + n × 50-byte records
  ```
- **Envelope check**: dims must fit the printer bed with ≥ 5 mm margins all
  around (Orca rejects plates that hug an edge — see `multipart-stl-plates`).
  Default constraint in the template is a 220 mm-cube bed (Flashforge AD5X).
- **Visual**: `stl_preview.py out.stl preview` → PNGs; inspect them. Vision
  models MISREAD raw meshes — trust the OpenSCAD source and section analysis
  over a vision model's guess when they disagree.
- Confirm final dims from the model (e.g. re-measure with a mesh reader)
  match the agreed table before presenting.

### 5. Hand off

Save the STL under the workspace models dir and hand to sibling `3dprinter`
for channels-confirm + slice + print.

## FDM printability constraints (0.4 mm nozzle reference)

| Feature | Rule | Why |
|---|---|---|
| Bed envelope | ≤ 210³ mm usable on a 220 bed (minus margins) | plate-edge rejection, brim |
| Min wall | ≥ 0.8 mm (2 perimeters); 1.2+ mm for functional | 0.4 mm nozzle, strength |
| Min feature / text | ≥ 1.2 mm relief; emboss better than deboss below 2 mm | extrusion fidelity |
| Min hole Ø | ≥ 1.2 mm; countersink/lead-in for screws | droop + first-layer squish |
| Sliding fit clearance | + 0.3–0.4 mm on the shaft | FDM tolerance band |
| Snap / press fits | +0.2 mm / −0.1–0.15 mm interference | PETG flex, PLA snaps brittle |
| Overhang | ≤ 45° unsupported; ≥ 60° or 10 mm bridges need support | droop |
| First-layer critical fits | compensate elephant foot ~0.1 mm (chamfer bottom edge) | layer-1 squish |
| Large flat bases | chamfer corners, avoid huge unsupported flats | warp |

## Pitfalls (learned)

- **Units**: OpenSCAD has NO units — everything is mm by convention. A part
  modeled in inches is 25.4× too big; sanity-check envelope after first render.
- **Boolean slivers**: `difference()` leaves zero-thickness walls when the
  cutter touches the outer surface — offset the cutter by ≥ 0.1 mm and never
  leave a shared-face boolean.
- **High `$fn` everywhere**: hundreds of smooth holes → multi-MB STL and slow
  slicing. Reserve 64 for visible curves; use `$fn=6`–`12` cylinders inside
  hidden cavities.
- **Render report is the truth**: check `Simple: yes` and the stderr triangle
  summary BEFORE previewing — CGAL refuses/silently fixes some degenerate CSG.
- **Naive chamfers bloat the part**: a bottom-edge chamfer built with
  `minkowski()` expands the footprint by the chamfer radius (40×25 declared
  became 40.5×25.5). Keep the box true to size and let the slicer's
  elephant-foot compensation handle layer-1 squish.

## See also

- Sibling `3dprinter` — slice → verify → print pipeline (OrcaSlicer headless,
  Flashforge LAN API, material channels).
- Sibling `multipart-stl-plates` — multi-shell STLs, plate packing, binary STL
  read/write, Orca plate-rejection rc codes.
- `templates/parametric-part.scad` — starter skeleton with named dims,
  asserts, and a printability pre-flight.
