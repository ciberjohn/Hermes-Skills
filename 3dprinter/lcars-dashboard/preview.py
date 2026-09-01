#!/usr/bin/env python3
"""LCARS-style rotating STL preview GIF renderer.

Pure numpy + Pillow (no OpenGL, no trimesh). Reads a binary or ASCII STL,
orbits a camera around the model (azimuth spins 360deg, fixed elevation),
renders LCARS-themed frames (orange-shaded solid on a dark plate with a
teal reticle) and assembles an animated GIF.

Usage:
  python3 preview.py <model.stl> <out.gif> [--size 360] [--frames 36]
                     [--fps 12] [--tilt 28] [--cap 12000] [--no-reticle]

Output GIF is looped forever, sized --size x --size.
"""
import argparse
import struct
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

# LCARS palette
BG      = (7, 7, 10)
ORANGE  = (255, 156, 0)
ORANGE_HI = (255, 190, 80)
# Material tone — warm PLA white: reads as a solid printed part (closer to the
# final object) instead of a glowing hollow shell. Override with --color.
MATERIAL    = (238, 233, 222)
MATERIAL_HI = (255, 255, 250)
EDGE    = (120, 115, 108)  # silhouette outline — defines edges on the material
TEAL    = (102, 204, 204)
PLATE_FILL = (14, 26, 34)
SHADOW  = (0, 0, 0)

# Bump when render output changes — the dashboard cache keys on it so browsers
# never serve a stale render under the same URL.
RENDER_VERSION = 3


def load_stl(path):
    """Return (n,3,3) float64 triangle array. Binary or ASCII."""
    with open(path, "rb") as f:
        head = f.read(80)
    if head[:5] == b"solid":
        return _load_ascii(path)
    return _load_binary(path, head)


def _load_binary(path, head):
    with open(path, "rb") as f:
        f.seek(80)
        n = struct.unpack("<I", f.read(4))[0]
        # 50 bytes per triangle: 12 normal + 36 verts + 2 attr
        raw = f.read(n * 50)
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(n, 50)
    tris = arr[:, 12:48].copy().view(np.float32).reshape(n, 3, 3)
    return tris.astype(np.float64)


def _load_ascii(path):
    tris = []
    cur = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "vertex":
                cur.append([float(x) for x in parts[1:4]])
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
    if not tris:
        raise ValueError("ASCII STL contains no vertices")
    return np.array(tris, dtype=np.float64)


def decimate(tris, cap):
    n = len(tris)
    if n <= cap:
        return tris
    step = n / cap
    idx = np.floor(np.arange(cap) * step).astype(int)
    return tris[idx]


def project(verts, cam, u, v, w, f, size, near=0.5):
    """Perspective projection. Returns (xs, ys, depths) arrays."""
    p = verts - cam
    px = p @ u
    py = p @ v
    pz = p @ w  # positive in front of camera
    with np.errstate(divide="ignore", invalid="ignore"):
        s = f / np.maximum(pz, near)
    xs = size / 2 + px * s
    ys = size / 2 - py * s
    return xs, ys, pz


def clip_poly_near(pts3, cam, w, near):
    """Sutherland-Hodgman clip of a closed 3D polygon to half-space pz>=near."""
    d = (pts3 - cam) @ w
    out = []
    n = len(pts3)
    for i in range(n):
        a = pts3[i]
        b = pts3[(i + 1) % n]
        da = d[i]
        db = d[(i + 1) % n]
        ain = da >= near
        bin_ = db >= near
        if ain:
            out.append(a)
        if ain != bin_:
            t = (near - da) / (db - da)
            out.append(a + t * (b - a))
    return np.array(out) if out else None


def frame_image(tris, normals, lo, hi, center, radius, theta, tilt_deg,
                size, f, light, reticle, plate_z, plate_radius,
                near_scale=0.15, outline=True):
    """Render one frame (PIL Image, RGB)."""
    tilt = np.radians(tilt_deg)
    near = max(radius * 0.15, 0.05)
    # camera orbit: azimuth theta, elevation tilt, distance 2.8x object radius
    cam = center + np.array([
        radius * 2.8 * np.cos(theta) * np.cos(tilt),
        radius * 2.8 * np.sin(theta) * np.cos(tilt),
        radius * 2.8 * np.sin(tilt),
    ])
    w = center - cam
    w /= np.linalg.norm(w)
    up = np.array([0.0, 0.0, 1.0])
    if abs(w[2]) > 0.98:
        up = np.array([0.0, 1.0, 0.0])
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)

    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)

    # ---- build plate (near-plane clipped, model overdraws it) ----
    if plate_radius > 0:
        circ = np.array([[np.cos(a), np.sin(a), 0.0] for a in
                         np.linspace(0, 2 * np.pi, 72)], dtype=np.float64)
        circ *= plate_radius
        circ += np.array([center[0], center[1], plate_z])
        clipped = clip_poly_near(circ, cam, w, near)
        if clipped is not None and len(clipped) >= 3:
            xs, ys, _ = project(clipped, cam, u, v, w, f, size, near)
            plate_pts = list(zip(xs, ys))
            d.polygon(plate_pts, fill=SHADOW)
            d.polygon(plate_pts, outline=None, fill=PLATE_FILL)
            d.line(plate_pts + [plate_pts[0]], fill=TEAL, width=2)

    # ---- model (painter's algorithm, far -> near) ----
    cents = tris.mean(axis=1)
    depth = (cents - cam) @ w
    order = np.argsort(depth)[::-1]

    view = cam - cents
    vn = np.linalg.norm(view, axis=1)
    vn[vn == 0] = 1
    facing = np.sum((view / vn[:, None]) * normals, axis=1) > 0  # toward camera
    lambert = np.clip(normals @ light, 0.0, 1.0)
    # fill light from the camera direction — keeps camera-facing faces readable
    viewdot = np.clip(np.sum((view / vn[:, None]) * normals, axis=1), 0.0, 1.0)
    # solid-object shading: high ambient so no face falls to background, plus
    # gentle depth fog for volume
    dmin, dmax = depth.min(), depth.max()
    fog = 1.0 - 0.18 * ((depth - dmin) / max(dmax - dmin, 1e-9))
    bright = np.clip(0.45 + 0.50 * lambert + 0.20 * viewdot, 0.0, 1.0) * fog

    img_mask = Image.new("L", (size, size), 0)
    dmask = ImageDraw.Draw(img_mask)
    for i in order:
        if not facing[i]:
            continue
        xs, ys, pz = project(tris[i], cam, u, v, w, f, size, near)
        if np.any(pz < near):
            continue  # triangle behind / too close to camera
        xs = np.clip(xs, -size * 0.5, size * 1.5)
        ys = np.clip(ys, -size * 0.5, size * 1.5)
        pts = list(zip(xs, ys))
        shade = bright[i]
        col = tuple(int(round(c * shade)) for c in MATERIAL)
        if lambert[i] > 0.9:  # specular kiss on bright faces
            col = tuple(min(255, int(round(c * 1.06))) for c in MATERIAL_HI)
        d.polygon(pts, fill=col)
        dmask.polygon(pts, fill=255)

    # ---- silhouette outline: true projected boundary, gives the part edges ----
    if outline:
        a = np.asarray(img_mask)
        shifted = np.stack([a] + [np.roll(a, s, axis=(0, 1)) for s in
                                  ((1, 0), (-1, 0), (0, 1), (0, -1))])
        edge = (a > 0) & (shifted.min(axis=0) == 0)
        arr = np.array(img, copy=True)
        arr[edge] = EDGE
        img = Image.fromarray(arr)

    # ---- reticle (decorative overlay, screen-space) ----
    if reticle:
        cxs = size / 2 + (center[0] - cam[0]) * f / max(1e-6, (center - cam) @ w)
        cys = size / 2 - (center[1] - cam[1]) * f / max(1e-6, (center - cam) @ w)
        rr = radius * f / max(1e-6, (center - cam) @ w) * 1.35
        d.ellipse([cxs - rr, cys - rr, cxs + rr, cys + rr],
                  outline=(TEAL[0], TEAL[1], TEAL[2], 70), width=1)
        d.ellipse([cxs - rr * 0.72, cys - rr * 0.72, cxs + rr * 0.72, cys + rr * 0.72],
                  outline=(TEAL[0], TEAL[1], TEAL[2], 40), width=1)
        for a in (0, 90, 180, 270):
            ax = np.cos(np.radians(a)) * rr
            ay = np.sin(np.radians(a)) * rr
            d.line([cxs + ax * 0.92, cys + ay * 0.92,
                    cxs + ax * 1.08, cys + ay * 1.08],
                   fill=(TEAL[0], TEAL[1], TEAL[2], 110), width=1)
    return img


def make_gif(tris, out, size=360, frames=36, fps=9, tilt=28, cap=12000,
             reticle=True, outline=True):
    tris = decimate(tris, cap)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nlen = np.linalg.norm(normals, axis=1)
    nlen[nlen == 0] = 1
    normals /= nlen[:, None]

    lo = tris.reshape(-1, 3).min(axis=0)
    hi = tris.reshape(-1, 3).max(axis=0)
    center = (lo + hi) / 2
    radius = (hi - lo).max() / 2
    plate_z = lo[2]
    plate_radius = max((hi[0] - lo[0]), (hi[1] - lo[1])) / 2 * 1.5
    fov = 42.0
    f = size / (2 * np.tan(np.radians(fov / 2)))
    light = np.array([0.45, 0.55, 0.75])
    light /= np.linalg.norm(light)

    imgs = []
    for fr in range(frames):
        theta = 2 * np.pi * fr / frames + np.radians(-30)
        imgs.append(frame_image(tris, normals, lo, hi, center, radius, theta,
                                tilt, size, f, light, reticle, plate_z,
                                plate_radius, outline=outline))
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=1000 / fps,
                 loop=0, optimize=True, disposal=2)
    return len(imgs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=360)
    ap.add_argument("--frames", type=int, default=36)
    ap.add_argument("--fps", type=float, default=9,
                    help="GIF playback speed (default 9 = ~4s per rotation)")
    ap.add_argument("--tilt", type=float, default=28)
    ap.add_argument("--cap", type=int, default=12000,
                    help="max triangles per frame (decimate larger meshes)")
    ap.add_argument("--no-reticle", action="store_true")
    ap.add_argument("--color", default=None, metavar="#RRGGBB",
                    help="material color override (default: warm PLA white)")
    args = ap.parse_args()

    if args.color:
        h = args.color.lstrip("#")
        rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        global MATERIAL, MATERIAL_HI
        MATERIAL = rgb
        MATERIAL_HI = tuple(min(255, int(c * 1.08)) for c in rgb)

    t0 = time.time()
    tris = load_stl(args.model)
    t1 = time.time()
    n = len(tris)
    frames = make_gif(tris, args.out, args.size, args.frames, args.fps,
                      args.tilt, args.cap, reticle=not args.no_reticle)
    t2 = time.time()
    print(f"loaded {n} tris ({t1-t0:.2f}s), rendered {frames} frames in "
          f"{t2-t1:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
