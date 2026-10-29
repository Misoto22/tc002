"""Rasterise the tc002 mark (web/static/favicon.svg) into the PNG and ICO icons browsers
that ignore SVG favicons ask for: Safari's tab, /favicon.ico, the iOS home screen.

favicon.svg is the source: its rounded square and circles are read from the file, drawn
with 4x4 supersampling, and written as PNG (zlib, no dependencies) and as an ICO that
wraps the 32 px PNG. tests/test_web.py checks the outputs match this script.

    uv run python scripts/render_favicon.py
"""

import re
import struct
import sys
import zlib
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "src/tc002/web/static"
SIZES = {"favicon-32.png": 32, "apple-touch-icon.png": 180}
SUPERSAMPLE = 4


def _rgb(hex_colour):
    return tuple(int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))


def shapes(svg):
    """(kind, geometry, rgb) for the mark's rect and circles, in drawing order."""
    rect = re.search(r'<rect width="(\d+)" height="(\d+)" rx="(\d+)" fill="(#\w{6})"', svg)
    out = [("rect", tuple(map(float, rect.groups()[:3])), _rgb(rect.group(4)))]
    for fill, body in re.findall(r'<g fill="(#\w{6})">(.*?)</g>', svg):
        for cx, cy, r in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"/>', body):
            out.append(("circle", (float(cx), float(cy), float(r)), _rgb(fill)))
    for cx, cy, r, fill in re.findall(
        r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="(#\w{6})"/>', svg
    ):
        out.append(("circle", (float(cx), float(cy), float(r)), _rgb(fill)))
    return out


def _inside(kind, geo, x, y):
    if kind == "circle":
        cx, cy, r = geo
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    w, h, rx = geo
    if not (0 <= x <= w and 0 <= y <= h):
        return False
    nx, ny = min(max(x, rx), w - rx), min(max(y, rx), h - rx)  # nearest point of the inner box
    return (x - nx) ** 2 + (y - ny) ** 2 <= rx * rx


def rasterise(svg, size, view=30.0):
    """RGBA rows of the mark at `size` x `size`."""
    marks = shapes(svg)
    n = SUPERSAMPLE
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            acc, covered = [0, 0, 0], 0
            for sy in range(n):
                for sx in range(n):
                    x = (px + (sx + 0.5) / n) * view / size
                    y = (py + (sy + 0.5) / n) * view / size
                    colour = None
                    for kind, geo, rgb in marks:
                        if _inside(kind, geo, x, y):
                            colour = rgb
                    if colour:
                        covered += 1
                        acc = [a + c for a, c in zip(acc, colour, strict=True)]
            alpha = covered * 255 // (n * n)
            rgb = [a // covered for a in acc] if covered else [0, 0, 0]
            row += bytes([*rgb, alpha])
        rows.append(bytes(row))
    return rows


def png(rows, size):
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def ico(png_bytes, size):
    """An ICO holding one PNG image (supported by every current browser)."""
    entry = struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(png_bytes), 6 + 16)
    return struct.pack("<HHH", 0, 1, 1) + entry + png_bytes


def outputs():
    """{file name: bytes} for every icon, from favicon.svg."""
    svg = (STATIC / "favicon.svg").read_text()
    files = {name: png(rasterise(svg, size), size) for name, size in SIZES.items()}
    files["favicon.ico"] = ico(files["favicon-32.png"], 32)
    return files


def main():
    for name, data in outputs().items():
        (STATIC / name).write_bytes(data)
        print(f"wrote {name} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
