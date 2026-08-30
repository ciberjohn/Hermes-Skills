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


def build_process_profile(outdir, base_proc, infill, supports, layer):
    """Copy the base process profile and apply CLI overrides; return temp path."""
    with open(base_proc) as fh:
        d = json.load(fh)
    if infill is not None:
        d["sparse_infill_density"] = f"{infill}%"
    if supports is not None:
        if supports == "none":
            d["support_enable"] = "0"
        else:
            d["support_enable"] = "1"
            d["support_type"] = "tree(auto)"
            if supports == "tree":
                d["support_style"] = "tree_slim"
    if layer is not None:
        d["layer_height"] = str(layer)
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

    fil = os.path.join(sl.get("profiles_dir", ""), FILAMENT_PROFILE[mat])
    base_proc = os.path.join(sl.get("profiles_dir", ""), args.profile if args.profile else PROCESS_PROFILE)
    missing = [p for p in (sl.get("orca_bin"), sl.get("machine_profile"), fil, base_proc) if not p or not os.path.exists(p)]
    if missing:
        sys.exit(f"missing files (check state.json slicer paths): {missing}")

    os.makedirs(sl["output_dir"], exist_ok=True)
    outdir = tempfile.mkdtemp(prefix="slice_", dir=sl["output_dir"])

    proc = build_process_profile(outdir, base_proc, infill, supports, layer)
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

    # --- Post-process: bed temps (OrcaSlicer 2.4.2 AD5X quirk) ---
    data = data.replace("M190 S35", f"M190 S{BED_TEMP[mat]['initial']}")
    data = data.replace("M140 S35", f"M140 S{BED_TEMP[mat]['normal']}")

    # --- Sanitize output name (path traversal guard) ---
    raw_name = args.name or os.path.splitext(os.path.basename(args.model))[0]
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", raw_name)
    final = os.path.join(sl["output_dir"], f"{safe_name}_{mat}.gcode")
    with open(final, "w", encoding="utf-8") as fh:
        fh.write(data)

    # --- Verify temps ---
    bed_cmds = re.findall(r"M1(?:90|40) S(\d+)", data)
    expected = {str(BED_TEMP[mat]["initial"]), str(BED_TEMP[mat]["normal"])}
    ok = len(bed_cmds) > 0 and all(t in expected for t in bed_cmds)

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
    }

    if args.json:
        print(json.dumps(info))
    else:
        print(f"gcode: {final}")
        print(f"material: {mat} | infill: {infill}% | layer: {layer} mm | supports: {supports}")
        print(f"layers: {info['layers']}")
        print(f"est time: {info['est_minutes']} min")
        print(f"bed temps verified: {ok}")

    shutil.rmtree(outdir, ignore_errors=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
