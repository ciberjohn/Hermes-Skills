#!/usr/bin/env python3
"""gcode_thumbnail.py — embed a 140x110 PNG preview into AD5X gcode.

Headless OrcaSlicer writes the `; thumbnails = 140x110/PNG` config line but
never embeds the actual image (thumbnail rendering happens in the GUI export
path), so the printer LCD shows no object preview — just the raw gcode text
("just see G"). This module renders the model (isometric mesh view, same
camera math as stl_preview.py) and returns the gcode comment block in the
Orca/Prusa format the firmware parses:

    ; thumbnail begin 140x110 <base64_len>
    ; <base64...>
    ; thumbnail end

Deps: numpy (required), Pillow (fast path). If Pillow is missing the renderer
falls back to stl_preview.py's pure-python scanline at low resolution.

Usage from slice.py:
    from gcode_thumbnail import thumbnail_block_for_stl
    block = thumbnail_block_for_stl(model_path)  # str or None
"""
import base64
import io
import os
import re
import struct

import numpy as np

THUMB_W, THUMB_H = 140, 110
VIEW_ISO = (-0.55, -0.55, -0.62)   # same iso as stl_preview.py
LIGHT = np.array([0.4, 0.6, 0.7], dtype=np.float64)
MATERIAL = np.array([0.95, 0.93, 0.88], dtype=np.float64)  # warm PLA-white
BG = (24, 26, 32)
B64_WIDTH = 76  # chars per base64 line (matches Prusa/Orca output)


def load_stl(path):
    """Load STL triangles (N,3,3) float32. Binary by size check, else ASCII."""
    with open(path, "rb") as fh:
        raw = fh.read()
    if len(raw) >= 84:
        n = struct.unpack("<I", raw[80:84])[0]
        if n > 0 and 84 + 50 * n == len(raw):
            body = np.frombuffer(raw, dtype=np.uint8, offset=84, count=50 * n)
            body = body.reshape(n, 50)
            seg = body[:, 12:48].copy()          # 3x float32 verts, contiguous
            tris = seg.view(np.float32).reshape(n, 3, 3).copy()
            return tris
    # ASCII fallback: collect vertex lines, group in threes
    text = raw.decode("utf-8", errors="replace")
    verts = re.findall(r"vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", text)
    if not verts or len(verts) % 3 != 0:
        raise ValueError(f"unrecognized STL format: {path}")
    arr = np.array([[float(a), float(b), float(c)] for a, b, c in verts], dtype=np.float32)
    return arr.reshape(-1, 3, 3)


def _camera(vd):
    vd = np.asarray(vd, dtype=np.float64)
    vd /= np.linalg.norm(vd)
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(vd, up))) > 0.99:
        up = np.array([0.0, 1.0, 0.0])
    u = np.cross(up, vd)
    u /= np.linalg.norm(u)
    v = np.cross(vd, u)
    return vd, u, v


def render_png(stl_path, w=THUMB_W, h=THUMB_H, supersample=2):
    """Render an iso thumbnail; returns PNG bytes (Pillow path or fallback)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return _render_png_fallback(stl_path, w, h)

    tris = load_stl(stl_path)
    vd, u, v = _camera(VIEW_ISO)
    verts = tris.reshape(-1, 3).astype(np.float64)
    lo = verts.min(axis=0)
    hi = verts.max(axis=0)
    c = (lo + hi) / 2
    p = verts - c
    px = p @ u
    py = p @ v

    W, H = w * supersample, h * supersample
    span_x = float(px.max() - px.min())
    span_y = float(py.max() - py.min())
    if span_x <= 0 or span_y <= 0:
        raise ValueError("degenerate model bbox")
    margin = 0.06
    s = min((W * (1 - 2 * margin)) / span_x, (H * (1 - 2 * margin)) / span_y)
    X = (px - px.min()) * s + (W - span_x * s) / 2.0
    Y = (py - py.min()) * s + (H - span_y * s) / 2.0

    centers = tris.mean(axis=1).astype(np.float64)
    depth = (centers - c) @ vd
    order = np.argsort(depth)[::-1]  # far first (painter's)

    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nlen = np.linalg.norm(nrm, axis=1)
    nlen[nlen == 0] = 1
    nrm = nrm / nlen[:, None]
    facing = (nrm @ vd) < 0  # outward normal toward camera

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    X3 = X.reshape(-1, 3)
    Y3 = Y.reshape(-1, 3)
    for i in order:
        if not facing[i]:
            continue
        b = max(0.0, float(nrm[i] @ LIGHT))
        col = np.clip(MATERIAL * (0.35 + 0.65 * b) * 255, 0, 255)
        pts = [(float(X3[i][j]), float(Y3[i][j])) for j in range(3)]
        draw.polygon(pts, fill=(int(col[0]), int(col[1]), int(col[2])))
    thumb = img.resize((w, h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    thumb.save(buf, format="PNG")
    return buf.getvalue()


def _render_png_fallback(stl_path, w, h):
    """Pure-numpy fallback: reuse stl_preview's square scanline, crop & pool."""
    import stl_preview
    tris = stl_preview.load_stl(stl_path)
    size = max(w, h) * 2
    img = stl_preview.render(tris, VIEW_ISO, size=size)
    # center-crop to aspect w:h then integer block-mean downsample
    crop_h = int(size * h / w)
    if crop_h > size:
        crop_h = size
    y0 = (size - crop_h) // 2
    img = img[y0:y0 + crop_h]
    fac = size // max(w, h)
    if fac >= 2:
        img = img[: (img.shape[0] // fac) * fac, : (img.shape[1] // fac) * fac]
        img = img.reshape(img.shape[0] // fac, fac, img.shape[1] // fac, fac, 3).mean(axis=(1, 3))
    img = np.clip(img, 0, 255).astype(np.uint8)
    # minimal PNG writer (as in stl_preview.save)
    import zlib
    hh, ww = img.shape[:2]
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(hh))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", ww, hh, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    return png


def thumbnail_block_for_stl(stl_path, w=THUMB_W, h=THUMB_H):
    """Return the gcode thumbnail comment block for an STL, or None on failure."""
    png = render_png(stl_path, w, h)
    b64 = base64.b64encode(png).decode("ascii")
    lines = [f"; thumbnail begin {w}x{h} {len(b64)}"]
    lines += ["; " + b64[i:i + B64_WIDTH] for i in range(0, len(b64), B64_WIDTH)]
    lines.append("; thumbnail end")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys
    png = render_png(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/gcode_thumb.png"
    with open(out, "wb") as fh:
        fh.write(png)
    print(f"wrote {out} ({len(png)} bytes)")
