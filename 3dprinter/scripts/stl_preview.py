#!/usr/bin/env python3
"""Render an STL from several orthographic views to PNG (no heavy deps).
Usage: stl_preview.py <model.stl> <out_prefix>
"""
import struct, sys, os
import numpy as np

def load_stl(path):
    with open(path, "rb") as f:
        f.seek(80)
        n = struct.unpack("<I", f.read(4))[0]
        tris = np.empty((n, 3, 3), dtype=np.float32)
        for i in range(n):
            f.read(12)  # normal
            for v in range(3):
                tris[i, v] = struct.unpack("<3f", f.read(12))
            f.read(2)
    return tris

def render(tris, view_dir, size=900, margin=0.06, light=(0.4, 0.6, 0.7)):
    vd = np.array(view_dir, dtype=np.float64)
    vd /= np.linalg.norm(vd)
    # camera basis
    up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(vd, up)) > 0.99:
        up = np.array([0.0, 1.0, 0.0])
    u = np.cross(up, vd); u /= np.linalg.norm(u)
    v = np.cross(vd, u)

    verts = tris.reshape(-1, 3).astype(np.float64)
    lo = verts.min(axis=0); hi = verts.max(axis=0)
    c = (lo + hi) / 2
    r = (hi - lo).max() / 2

    # project
    p = verts - c
    px = p @ u
    py = p @ v
    pz = p @ vd  # depth (smaller = closer)

    xmin, xmax = px.min(), px.max()
    ymin, ymax = py.min(), py.max()
    s = (size * (1 - 2 * margin)) / max(xmax - xmin, ymax - ymin)
    X = ((px - xmin) * s + margin * size).astype(np.int32)
    Y = ((py - ymin) * s + margin * size).astype(np.int32)

    # per-triangle depth + normal
    t_cent = tris.mean(axis=1)
    depth = (t_cent - c) @ vd
    order = np.argsort(depth)[::-1]  # far first

    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nlen = np.linalg.norm(nrm, axis=1)
    nlen[nlen == 0] = 1
    nrm /= nlen[:, None]
    # face away from camera -> backface, skip
    facing = (nrm @ vd) < 0

    img = np.zeros((size, size, 3), dtype=np.float32)
    img[:] = 0.13  # dark bg
    for i in order:
        if not facing[i]:
            continue
        xs = X[i * 3:i * 3 + 3]; ys = Y[i * 3:i * 3 + 3]
        b = np.maximum(0, nrm[i] @ np.array(light, dtype=np.float64))
        col = np.array([0.95, 0.93, 0.88]) * (0.35 + 0.65 * b)
        # scanline fill
        y0, y1 = int(ys.min()), int(ys.max())
        for yy in range(max(0, y0), min(size - 1, y1) + 1):
            xs_edge = []
            for e in range(3):
                xa, ya = xs[e], ys[e]
                xb, yb = xs[(e + 1) % 3], ys[(e + 1) % 3]
                if ya == yb:
                    continue
                if (ya <= yy < yb) or (yb <= yy < ya):
                    t = (yy - ya) / (yb - ya)
                    xs_edge.append(xa + t * (xb - xa))
            if len(xs_edge) >= 2:
                xl, xr = int(min(xs_edge)), int(max(xs_edge))
                img[yy, max(0, xl):min(size - 1, xr) + 1] = col
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)

def save(img, path):
    # minimal PNG writer via zlib
    import zlib, struct as st
    h, w = img.shape[:2]
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))
    def chunk(tag, data):
        c = st.pack(">I", len(data)) + tag + data
        return c + st.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", st.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)

def main():
    path, prefix = sys.argv[1], sys.argv[2]
    tris = load_stl(path)
    print(f"loaded {len(tris)} triangles")
    views = {
        "front": (0, -1, 0),   # looking along -Y
        "back":  (0, 1, 0),
        "right": (1, 0, 0),
        "left":  (-1, 0, 0),
        "top":   (0, 0, -1),
        "iso":   (-0.55, -0.55, -0.62),
    }
    for name, vd in views.items():
        img = render(tris, vd)
        out = f"{prefix}_{name}.png"
        save(img, out)
        print("wrote", out)

if __name__ == "__main__":
    main()
