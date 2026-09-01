#!/usr/bin/env python3
"""slice.py — headless OrcaSlicer slicing for the Flashforge AD5X (3dprinter skill).

Usage:
  slice.py <model.stl|model.3mf> --material PLA|PETG [options]

Options:
  --infill PCT     infill percentage (default: from state defaults)
  --supports MODE  auto|none|tree (default: from state defaults)
  --layer MM       layer height (default: from state defaults)
  --profile NAME   process profile filename in profiles_dir
                   (default: Spock Quality 0.20 @FF AD5X.json)
  --name NAME      output gcode name (default: <model>_<MATERIAL>)
  --json           machine-readable output

Pipeline: slice with OrcaSlicer CLI -> post-process bed temps (OrcaSlicer 2.4.2
AD5X quirk ignores filament bed keys; values come from the SOP material table)
-> verify temps -> report.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# State file: override with 3DPRINTER_STATE if set.
STATE = os.environ.get("3DPRINTER_STATE", os.path.expanduser("~/3dprinter/state.json"))

# Bed temperatures from the AD5X SOP material table (see SKILL.md).
# PLA: 60-65 C bed, PETG: 80 C bed.
BED_TEMP = {
    "PLA": {"normal": 62, "initial": 65},
    "PETG": {"normal": 80, "initial": 80},
}

FILAMENT_PROFILE = {
    "PLA": "Spock PLA @FF AD5X.json",
    "PETG": "Spock PETG @FF AD5X.json",
}

PROCESS_PROFILE = "Spock Quality 0.20 @FF AD5X.json"


def load_state():
    if not os.path.exists(STATE):
        sys.exit(f"state file not found: {STATE} — answer the install prompt to create it")
    with open(STATE) as fh:
        st = json.load(fh)
    # Expand ~ in every slicer path (documented example values use ~/).
    sl = st.get("slicer", {})
    for key in ("orca_bin", "datadir", "machine_profile", "profiles_dir", "output_dir"):
        if sl.get(key):
            sl[key] = os.path.expanduser(sl[key])
    return st


def model_base_contact_mm2(path):
    """Flat area touching the bed (triangles near Z=0 with near-horizontal normals).
    Returns (area_mm2, height_mm) or None if the STL can't be parsed.
    Catches the 'model standing on a knife edge' class of orientation errors."""
    try:
        import struct as _struct
        import numpy as np
    except ImportError:
        return None
    try:
        with open(path, "rb") as fh:
            head = fh.read(84)
            if len(head) != 84:
                return None
            n = _struct.unpack("<I", head[80:84])[0]
            if n <= 0 or n > 5_000_000:
                return None
            tris = np.empty((n, 3, 3), dtype=np.float64)
            for i in range(n):
                fh.read(12)
                for v in range(3):
                    tris[i, v] = _struct.unpack("<3f", fh.read(12))
                fh.read(2)
    except Exception:
        return None
    a = tris[:, 1] - tris[:, 0]
    b = tris[:, 2] - tris[:, 0]
    cr = np.cross(a, b)
    areas = 0.5 * np.sqrt((cr ** 2).sum(axis=1))
    nlen = np.sqrt((cr ** 2).sum(axis=1))
    nz = np.zeros_like(nlen)
    m = nlen > 0
    nz[m] = cr[m, 2] / nlen[m]
    zmin = tris[:, :, 2].min()
    zcen = tris[:, :, 2].mean(axis=1)
    flat = (np.abs(zcen - zmin) < 0.3) & (np.abs(nz) > 0.9)
    base = float(areas[flat].sum())
    height = float(tris[:, :, 2].max() - zmin)
    return base, height


def build_process_profile(outdir, base_proc, infill, supports, layer, brim, raft):
    """Copy the base process profile and apply CLI overrides; return temp path."""
    with open(base_proc) as fh:
        d = json.load(fh)
    if infill is not None:
        d["sparse_infill_density"] = f"{infill}%"
    if supports is not None:
        if supports == "none":
            d["enable_support"] = "0"
        else:
            d["enable_support"] = "1"
            d["support_type"] = "tree(auto)"
            if supports == "tree":
                d["support_style"] = "tree_slim"
    if layer is not None:
        d["layer_height"] = str(layer)
    if brim is not None:
        d["brim_type"] = "brim"
        d["brim_width"] = str(brim)
    if raft is not None:
        d["raft_layers"] = str(raft)
        d["raft_contact_distance"] = "0.25"  # easy pop-off
    fd, path = tempfile.mkstemp(suffix=".json", prefix="proc_override_", dir=outdir)
    with os.fdopen(fd, "w") as fh:
        json.dump(d, fh)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--material", required=True, choices=sorted(BED_TEMP))
    ap.add_argument("--infill", default=None, type=int)
    ap.add_argument("--supports", default=None, choices=["auto", "none", "tree"])
    ap.add_argument("--layer", default=None, type=float)
    ap.add_argument("--profile", default=None, help="process profile filename (default: Spock Quality 0.20)")
    ap.add_argument("--brim", default=None, type=int, help="outer brim width in mm (default: profile's auto brim)")
    ap.add_argument("--raft", default=None, type=int, help="raft layers (0.25mm contact distance, easy pop-off)")
    ap.add_argument("--nozzle", default=None, type=int, help="nozzle temp override, e.g. 200 (keeps the 245C purge)")
    ap.add_argument("--bed", default=None, help="bed temps INITIAL,NORMAL, e.g. 70,65 (default from SOP table)")
    ap.add_argument("--name", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    st = load_state()
    sl = st["slicer"]
    mat = args.material.upper()
    defaults = st.get("defaults", {})

    # Effective parameters: CLI overrides state defaults.
    infill = args.infill if args.infill is not None else defaults.get("infill_percent", 15)
    supports = args.supports if args.supports is not None else defaults.get("supports", "auto")
    layer = args.layer if args.layer is not None else defaults.get("layer_height", 0.2)

    if not os.path.exists(args.model):
        sys.exit(f"model not found: {args.model}")

    # --- Orientation pre-check: warn if the model has almost no flat base ---
    base_info = model_base_contact_mm2(args.model)
    if base_info:
        base_mm2, height_mm = base_info
        if base_mm2 < 500:
            print(f"WARNING: base contact at Z=0 is only {base_mm2:.0f} mm^2 "
                  f"(model height {height_mm:.0f} mm) — likely WRONG ORIENTATION. "
                  f"Rotate the model so a flat face sits on the bed before slicing.",
                  file=sys.stderr)
    else:
        base_mm2 = None

    fil = os.path.join(sl.get("profiles_dir", ""), FILAMENT_PROFILE[mat])
    base_proc = os.path.join(sl.get("profiles_dir", ""), args.profile if args.profile else PROCESS_PROFILE)
    missing = [p for p in (sl.get("orca_bin"), sl.get("machine_profile"), fil, base_proc) if not p or not os.path.exists(p)]
    if missing:
        sys.exit(f"missing files (check state.json slicer paths): {missing}")

    os.makedirs(sl["output_dir"], exist_ok=True)
    outdir = tempfile.mkdtemp(prefix="slice_", dir=sl["output_dir"])

    proc = build_process_profile(outdir, base_proc, infill, supports, layer, args.brim, args.raft)
    cmd = [sl["orca_bin"]]
    if sl.get("datadir"):
        cmd += ["--datadir", sl["datadir"]]
    cmd += [
        "--load-settings", f'{sl["machine_profile"]};{proc}',
        "--load-filaments", fil,
        "--slice", "0",
        "--outputdir", outdir,
        args.model,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        sys.exit(f"orca_bin not found: {sl['orca_bin']}")
    except subprocess.TimeoutExpired:
        sys.exit("slice timed out")

    gcode = os.path.join(outdir, "plate_1.gcode")
    if r.returncode != 0 or not os.path.exists(gcode):
        sys.exit(f"slice failed (rc={r.returncode}): {r.stdout[-400:]} {r.stderr[-400:]}")

    data = open(gcode, encoding="utf-8", errors="replace").read()

    # --- Support verification gate: requested supports MUST actually be in the
    # gcode (bug class: wrong key name -> silently sliced with enable_support=0
    # and printed into thin air, 2026-09-01 incident). ---
    if supports != "none":
        m = re.search(r"enable_support\s*=\s*([01])", data)
        gen = m.group(1) if m else None
        if gen != "1":
            sys.exit(
                f"SUPPORT FAILURE: --supports {supports} requested but gcode has "
                f"enable_support={gen or 'MISSING'}. Fix the process profile / "
                f"override mechanism; do NOT print this gcode."
            )

    # --- Post-process: bed temps (OrcaSlicer 2.4.2 AD5X quirk) ---
    bed_init, bed_norm = BED_TEMP[mat]["initial"], BED_TEMP[mat]["normal"]
    if args.bed:
        try:
            bed_init, bed_norm = [int(x.strip()) for x in args.bed.split(",")]
        except ValueError:
            sys.exit("--bed must be INITIAL,NORMAL e.g. 70,65")
    data = data.replace("M190 S35", f"M190 S{bed_init}")
    data = data.replace("M140 S35", f"M140 S{bed_norm}")

    # --- Nozzle temp override (keeps the PETG-safe 245C purge untouched) ---
    if args.nozzle is not None:
        data = re.sub(r"M104 S215", f"M104 S{args.nozzle}", data)
        data = re.sub(r"M109 S215", f"M109 S{args.nozzle}", data)

    # --- Sanitize output name (path traversal guard) ---
    raw_name = args.name or os.path.splitext(os.path.basename(args.model))[0]
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", raw_name)
    final = os.path.join(sl["output_dir"], f"{safe_name}_{mat}.gcode")
    with open(final, "w", encoding="utf-8") as fh:
        fh.write(data)

    # --- Verify temps ---
    bed_cmds = re.findall(r"M1(?:90|40) S(\d+)", data)
    expected = {str(bed_init), str(bed_norm)}
    ok = len(bed_cmds) > 0 and all(t in expected for t in bed_cmds)
    if args.nozzle is not None:
        ok = ok and f"M109 S{args.nozzle}" in data

    layers_n = re.search(r"total layer number: (\d+)", data)
    time_m = re.search(r"M73 P0 R(\d+)", data)
    info = {
        "gcode": final,
        "material": mat,
        "infill": infill,
        "layer_height": layer,
        "supports": supports,
        "layers": int(layers_n.group(1)) if layers_n else None,
        "est_minutes": int(time_m.group(1)) if time_m else None,
        "bed_verified": ok,
        "base_mm2": base_mm2,
    }

    if args.json:
        print(json.dumps(info))
    else:
        print(f"gcode: {final}")
        print(f"material: {mat} | infill: {infill}% | layer: {layer} mm | supports: {supports}")
        if base_mm2 is not None:
            print(f"base contact at Z=0: {base_mm2:.0f} mm^2")
        print(f"layers: {info['layers']}")
        print(f"est time: {info['est_minutes']} min")
        print(f"bed temps verified: {ok}")

    shutil.rmtree(outdir, ignore_errors=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
