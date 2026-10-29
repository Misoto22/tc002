"""A 12 px pixel font covering Chinese (simplified and traditional), for messages.

Glyphs come from data/cjk12.txt.gz (Fusion Pixel Font, OFL; see data/SOURCES.md and
scripts/vendor_cjk_font.py). The table loads on first use and decodes each glyph only
when drawn, so screens that never show Chinese pay nothing.
"""

import gzip
from importlib import resources

HEIGHT = 12


class _Table:
    """Mapping char -> glyph spec ("#.#|.#." rows), the shape font.py's tables use."""

    def __init__(self):
        self._raw = None
        self._specs = {}

    def _load(self):
        data = resources.files("tc002.render").joinpath("data/cjk12.txt.gz").read_bytes()
        self._raw = {}
        for line in gzip.decompress(data).decode().splitlines():
            cp, width, rows = line.split(" ")
            self._raw[chr(int(cp, 16))] = (int(width), rows)

    def get(self, ch, default=None):
        if ch in self._specs:
            return self._specs[ch]
        if self._raw is None:
            self._load()
        if ch not in self._raw:
            return default
        width, rows = self._raw[ch]
        spec = "|".join(
            "".join("#" if int(r, 16) >> (width - 1 - i) & 1 else "." for i in range(width))
            for r in rows.split(",")
        )
        self._specs[ch] = spec
        return spec

    def __getitem__(self, ch):
        spec = self.get(ch)
        if spec is None:
            raise KeyError(ch)
        return spec

    def __contains__(self, ch):
        return self.get(ch) is not None


FONT = _Table()
