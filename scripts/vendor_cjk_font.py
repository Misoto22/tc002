"""Vendor a 12 px CJK pixel font for the clock: src/tc002/render/data/cjk12.txt.gz.

Source: Fusion Pixel Font (github.com/TakWolf/fusion-pixel-font), 12 px monospaced, the
Simplified Chinese BDF, SIL Open Font License 1.1. Kept: printable ASCII, CJK and
full-width punctuation, every GB2312 (simplified) and Big5 (traditional) character.
Each line is `<code point hex> <width> <12 rows of bits, hex, comma separated>`.
Run again to refresh: `uv run python scripts/vendor_cjk_font.py [downloaded.zip]` (pass the
release zip when GitHub downloads are slow; it is ~37 MB).
"""

import gzip
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

RELEASE = "2026.10.25"
ASSET = f"fusion-pixel-font-12px-monospaced-bdf-v{RELEASE}.zip"
URL = f"https://github.com/TakWolf/fusion-pixel-font/releases/download/{RELEASE}/{ASSET}"
OUT = Path(__file__).resolve().parents[1] / "src/tc002/render/data"
CELL = 12


def wanted():
    chars = {chr(c) for c in range(0x20, 0x7F)}
    chars |= {chr(c) for c in range(0x3000, 0x3040)} | {chr(c) for c in range(0xFF01, 0xFF5F)}
    for codec, rows, cols in (
        ("gb2312", range(0xB0, 0xF8), range(0xA1, 0xFF)),
        ("big5", range(0xA4, 0xFA), range(0x40, 0xFF)),
    ):
        for hi in rows:
            for lo in cols:
                try:
                    chars.add(bytes((hi, lo)).decode(codec))
                except UnicodeDecodeError:
                    continue
    # punctuation common in Chinese text that sits outside the CJK blocks:
    # middle dot, times, divide, em dash, curly quotes, ellipsis
    chars |= {chr(c) for c in (0xB7, 0xD7, 0xF7, 0x2014, 0x201C, 0x201D, 0x2018, 0x2019, 0x2026)}
    return chars


def glyphs(bdf):
    """(char, width, rows) from a BDF, each placed in a 12-row cell on the font's baseline."""
    ascent, out, cur = None, [], None
    for line in bdf.splitlines():
        key, _, rest = line.partition(" ")
        if key == "FONT_ASCENT":
            ascent = int(rest)
        elif key == "STARTCHAR":
            cur = {"bitmap": None}
        elif key == "ENCODING":
            cur["cp"] = int(rest.split()[0])
        elif key == "DWIDTH":
            cur["dwidth"] = int(rest.split()[0])
        elif key == "BBX":
            cur["bbx"] = [int(v) for v in rest.split()]
        elif key == "BITMAP":
            cur["bitmap"] = []
        elif key == "ENDCHAR":
            w, h, xoff, yoff = cur["bbx"]
            rows = [0] * CELL
            top = ascent - (yoff + h)
            for i, hexrow in enumerate(cur["bitmap"]):
                y = top + i
                if 0 <= y < CELL:
                    bits = int(hexrow, 16) >> (len(hexrow) * 4 - w)  # left-aligned in the hex
                    rows[y] = bits << max(0, cur["dwidth"] - w - xoff)
            out.append((chr(cur["cp"]), cur["dwidth"], rows))
            cur = None
        elif cur is not None and cur.get("bitmap") is not None:
            cur["bitmap"].append(line.strip())
    return out


def main():
    if len(sys.argv) > 1:
        archive = zipfile.ZipFile(sys.argv[1])
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "tc002-vendor-font"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            archive = zipfile.ZipFile(io.BytesIO(resp.read()))
    name = next(n for n in archive.namelist() if n.endswith(".bdf") and "zh_hans" in n)
    keep = wanted()
    lines = [
        f"{ord(ch):x} {width} {','.join(f'{r:x}' for r in rows)}"
        for ch, width, rows in glyphs(archive.read(name).decode("utf-8"))
        if ch in keep
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cjk12.txt.gz").write_bytes(gzip.compress("\n".join(lines).encode(), mtime=0))
    # the font merges several OFL fonts; ship every licence it carries
    licences = [n for n in archive.namelist() if n.upper().endswith("OFL.TXT")]
    licence = licences[0] if licences else None
    (OUT / "SOURCES.md").write_text(
        "# Clock fonts\n\n"
        f"`cjk12.txt.gz`: {len(lines)} glyphs from Fusion Pixel Font {RELEASE} "
        f"(`{name}`), SIL Open Font License 1.1, {URL}.\n"
        "Regenerate with `uv run python scripts/vendor_cjk_font.py`.\n"
    )
    for path in licences:
        target = "OFL.txt" if "/" not in path else f"OFL-{path.split('/')[-2]}.txt"
        (OUT / target).write_bytes(archive.read(path))
    print(json.dumps({"glyphs": len(lines), "bdf": name, "licence": licence}))


if __name__ == "__main__":
    main()
