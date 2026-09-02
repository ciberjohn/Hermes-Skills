#!/usr/bin/env python3
"""materialize_profiles.py — bake the vendor `inherits` chain into Spock profiles.

WHY: headless OrcaSlicer CLI does NOT resolve a profile's `inherits` ancestors
(verified 2026-09-02: slices fell back to Orca's generic defaults — outer walls
60 mm/s, infill 100, travel 120, default accel 500, and worst of all
filament_max_volumetric_speed = 2 mm³/s — instead of the FlashForge AD5X
vendor chain values outer 200 / inner 300 / infill 270 / travel 500 /
volumetric 25). The GUI resolves the chain; the CLI does not. Fix: bake every
key from the resolvable ancestor files directly into the Spock profile so the
profile is self-contained and the CLI output matches the GUI output.

Usage (all paths required, no baked-in machine paths):
  python3 materialize_profiles.py \
      --profiles-dir <dir with Spock profile JSONs> \
      --orca-resources <OrcaSlicer resources/profiles dir> \
      --output <copy dir 1> [--output <copy dir 2> ...]

  --profiles-dir   where the Spock *.json files live (source + default output)
  --orca-resources the extracted OrcaSlicer AppImage resources/profiles dir
                   (vendor JSON trees: <vendor>/process, <vendor>/filament)
  --output         extra directories that receive the same baked files
                   (e.g. skill assets + public repo assets); repeatable

Example (João's fleet):
  python3 materialize_profiles.py \
    --profiles-dir ~/.hermes/profiles/spock/home/3dprint/profiles \
    --orca-resources ~/.hermes/profiles/spock/home/3dprint/slicer/squashfs-root/resources/profiles \
    --output ~/.hermes/profiles/spock/skills/3dprinting/3dprinter/assets/profiles \
    --output ~/Hermes-Skills/3dprinter/assets/profiles

Run after ANY edit to a profile JSON, or slices silently regress to slow
generic defaults. Verify after slicing: outer_wall_speed = 200 and
filament_max_volumetric_speed = 25 in the gcode config dump.
"""
import argparse
import json
import os
import sys


def resolve_chain(inherits, search_root, kind, acc=None):
    """Collect ancestor dicts root-ward->leaf-ward from the file `inherits` names.
    Stops when no vendor dir contains a file for the name (built-in C++ default).
    `kind` = 'process' | 'filament' selects the vendor subdirectory searched."""
    if acc is None:
        acc = []
    if not inherits:
        return acc
    if not os.path.isdir(search_root):
        return acc
    for vendor in sorted(os.listdir(search_root)):
        cand = os.path.join(search_root, vendor, kind, inherits + ".json")
        if os.path.exists(cand):
            with open(cand) as fh:
                d = json.load(fh)
            resolve_chain(d.get("inherits"), search_root, kind, acc)
            acc.append(d)
            return acc
    return acc


def materialize(leaf_path, search_root):
    with open(leaf_path) as fh:
        leaf = json.load(fh)
    kind = leaf.get("type")
    if kind not in ("process", "filament"):
        return None, kind, []
    chain = resolve_chain(leaf.get("inherits"), search_root, kind)
    merged = {}
    for anc in chain:
        merged.update(anc)
    merged.update(leaf)
    return merged, kind, chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", required=True,
                    help="directory containing the Spock/leaf profile JSONs")
    ap.add_argument("--orca-resources", required=True,
                    help="OrcaSlicer resources/profiles dir (vendor trees)")
    ap.add_argument("--output", action="append", default=[],
                    help="extra output dir to receive the baked files (repeatable)")
    ap.add_argument("--include", action="append", default=[],
                    help="only bake files with these basenames (repeatable); "
                         "omit to bake every *.json in --profiles-dir")
    args = ap.parse_args()

    out_dirs = [args.profiles_dir] + args.output
    for d in out_dirs:
        os.makedirs(d, exist_ok=True)

    changed = 0
    for name in sorted(os.listdir(args.profiles_dir)):
        if not name.endswith(".json"):
            continue
        if args.include and name not in args.include:
            continue
        leaf_path = os.path.join(args.profiles_dir, name)
        merged, kind, chain = materialize(leaf_path, args.orca_resources)
        if merged is None:
            print(f"SKIP {name}: unsupported type {kind!r}")
            continue
        print(f"== {name} (kind={kind}, ancestors baked: {len(chain)})")
        for anc in chain:
            print(f"    <- {anc.get('name')} ({len(anc)} keys)")
        for out_dir in out_dirs:
            out = os.path.join(out_dir, name)
            with open(out, "w") as fh:
                json.dump(merged, fh, indent=2)
                fh.write("\n")
            print(f"    wrote {out} ({len(merged)} keys)")
            changed += 1
    print(f"done, {changed} files written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
