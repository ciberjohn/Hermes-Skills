#!/usr/bin/env python3
"""Render a plate preview from sliced gcode toolpaths (top-down + front view).
Coloring: model = viridis-by-Z, supports = orange, raft = gray.
Usage: plate_preview.py <file.gcode> <out_prefix>
"""
import re, sys
from PIL import Image, ImageDraw

GCODE = sys.argv[1]
PREFIX = sys.argv[2]

segments = []  # (x1,y1,x2,y2,z,kind) kind in {"model","support","raft"}
cur_type = "model"
cur_z = 0.0
pos = (0.0, 0.0)
E_prev = 0.0

G1_RE = re.compile(r"^G1\b")
X_RE = re.compile(r"X([-\d.]+)")
Y_RE = re.compile(r"Y([-\d.]+)")
Z_RE = re.compile(r"Z([-\d.]+)")
E_RE = re.compile(r"E([-\d.]+)")

with open(GCODE, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if line.startswith(";LAYER_CHANGE"):
            continue
        if line.startswith(";Z:"):
            cur_z = float(line[3:])
            continue
        if line.startswith(";TYPE:"):
            t = line[6:].strip().lower()
            if t.startswith("support"):
                cur_type = "support"
            elif "raft" in t:
                cur_type = "raft"
            elif t in ("custom",):
                cur_type = "model"
            else:
                cur_type = "model"
            continue
        if not G1_RE.match(line):
            continue
        has_e = "E" in line
        has_xy = ("X" in line) or ("Y" in line)
        if has_e and has_xy:
            m = X_RE.search(line)
            nx = float(m.group(1)) if m else pos[0]
            m = Y_RE.search(line)
            ny = float(m.group(1)) if m else pos[1]
            segments.append((pos[0], pos[1], nx, ny, cur_z, cur_type))
            pos = (nx, ny)
        elif has_xy:
            m = X_RE.search(line)
            nx = float(m.group(1)) if m else pos[0]
            m = Y_RE.search(line)
            ny = float(m.group(1)) if m else pos[1]
            pos = (nx, ny)
        # Z-only moves (layer change) update nothing for X/Y

if not segments:
    sys.exit("no extrusion segments found")

zmin = min(s[4] for s in segments)
zmax = max(s[4] for s in segments)
print(f"segments: {len(segments)}  z range {zmin:.2f} .. {zmax:.2f}")

def viridis(t):
    # simple blue->green->yellow ramp
    if t < 0.33:
        return (12, 40, int(165 + 90 * (t / 0.33)))
    if t < 0.66:
        return (30, int(160 + 60 * ((t - 0.33) / 0.33)), int(120 - 60 * ((t - 0.33) / 0.33)))
    return (int(235 - 60 * ((t - 0.66) / 0.34)), 220, 60)

def color_for(kind, z):
    if kind == "support":
        return (240, 120, 30)
    if kind == "raft":
        return (180, 180, 180)
    return viridis((z - zmin) / max(zmax - zmin, 1e-9))

def render_topdown():
    S = 980
    M = 70
    bed = 220.0
    img = Image.new("RGB", (S, S), (24, 26, 32))
    d = ImageDraw.Draw(img)
    # bed
    b0 = M
    b1 = S - M
    d.rectangle([b0, b0, b1, b1], outline=(90, 95, 110), width=2)
    d.text((10, 10), "Mani Dock Max — plate preview (top-down, 220x220 bed)", fill=(220, 220, 220))
    d.text((10, 30), f"model 74x104 mm @ Z0  |  blue=low .. yellow=high  |  orange=support  |  gray=raft", fill=(160, 165, 180))
    scale = (b1 - b0) / bed
    for x1, y1, x2, y2, z, kind in segments:
        c = color_for(kind, z)
        d.line([b0 + x1 * scale, b0 + y1 * scale, b0 + x2 * scale, b0 + y2 * scale], fill=c, width=2)
    # scale ticks
    for mm in (0, 50, 100, 150, 200):
        px = b0 + mm * scale
        d.line([px, b1 + 8, px, b1 + 16], fill=(200, 200, 200))
        d.text((px - 6, b1 + 18), str(mm), fill=(200, 200, 200))
    out = f"{PREFIX}_plate.png"
    img.save(out)
    print("wrote", out)

# simpler front: rewrite without the typo
def render_front2():
    W, H = 1200, 700
    M = 90
    bed = 220.0
    zmax_f = max(s[4] for s in segments)
    z_scale = (H - 2 * M) / max(zmax_f, 1.0)
    x_scale = (W - 2 * M) / bed
    img = Image.new("RGB", (W, H), (24, 26, 32))
    d = ImageDraw.Draw(img)
    d.line([M, H - M, W - M, H - M], fill=(90, 95, 110), width=2)
    d.text((10, 10), "Mani Dock Max — front view (Y vs Z)", fill=(220, 220, 220))
    d.text((10, 30), "gray = raft (3 layers)  |  orange = tree supports  |  model rises to ~44 mm", fill=(160, 165, 180))
    for x1, y1, x2, y2, z, kind in segments:
        c = color_for(kind, z)
        d.line([M + y1 * x_scale, H - M - z * z_scale,
                M + y2 * x_scale, H - M - z * z_scale], fill=c, width=2)
    d.text((10, H - 40), "Y (mm) 0 .. 220  |  Z (mm) 0 .. %.0f" % zmax_f, fill=(200, 200, 200))
    out = f"{PREFIX}_front.png"
    img.save(out)
    print("wrote", out)

render_topdown()
render_front2()
