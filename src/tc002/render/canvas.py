"""A 52x16 RGB frame buffer; animations are sequences of these (see anim.py)."""

from . import font

WIDTH, HEIGHT = 52, 16


def rgb(color):
    """'#RRGGBB' or an int 0xRRGGBB -> int."""
    if isinstance(color, int):
        return color
    return int(color.lstrip("#"), 16)


def dim(color, factor):
    """Scale a color's brightness; factor 0..1."""
    c = rgb(color)
    return sum(int(((c >> s) & 0xFF) * factor) << s for s in (16, 8, 0))


def mix(a, b, t):
    """Linear blend from color a (t=0) to color b (t=1)."""
    a, b = rgb(a), rgb(b)
    return sum(
        int(((a >> s) & 0xFF) + (((b >> s) & 0xFF) - ((a >> s) & 0xFF)) * t) << s
        for s in (16, 8, 0)
    )


class Canvas:
    """Pixel buffer drawn on locally, then encoded into a GIF frame."""

    def __init__(self, background=0):
        self.px = [rgb(background)] * (WIDTH * HEIGHT)

    def set(self, x, y, color):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            self.px[y * WIDTH + x] = rgb(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def border(self, color):
        self.rect(0, 0, WIDTH, 1, color)
        self.rect(0, HEIGHT - 1, WIDTH, 1, color)
        self.rect(0, 0, 1, HEIGHT, color)
        self.rect(WIDTH - 1, 0, 1, HEIGHT, color)

    def sprite(self, x, y, rows, color):
        """Draw a '#'/'.' pattern (list of strings) at x, y."""
        for dy, row in enumerate(rows):
            for dx, c in enumerate(row):
                if c == "#":
                    self.set(x + dx, y + dy, color)

    def text(self, x, y, text, color, big=True, spacing=None, table=None):
        """Draw text with a pixel font (`table`, else BIG or SMALL); returns the x after it."""
        table = table or (font.BIG if big else font.SMALL)
        spacing = font.letter_spacing(table) if spacing is None else spacing
        for ch in text:
            rows = font.glyph(table, ch)
            for dy, row in enumerate(rows):
                for dx, on in enumerate(row):
                    if on:
                        self.set(x + dx, y + dy, color)
            x += len(rows[0]) + spacing
        return x

    def text_centered(self, y, text, color, big=True):
        table = font.BIG if big else font.SMALL
        x = (WIDTH - font.text_width(table, text)) // 2
        self.text(x, y, text, color, big)

    def get(self, x, y):
        return self.px[y * WIDTH + x] if 0 <= x < WIDTH and 0 <= y < HEIGHT else 0

    def ansi(self):
        """Truecolor terminal preview, two pixels per character cell (upper half block)."""
        lines = []
        for y in range(0, HEIGHT, 2):
            cells = []
            for x in range(WIDTH):
                top, bottom = self.px[y * WIDTH + x], self.px[(y + 1) * WIDTH + x]
                cells.append(
                    f"\x1b[38;2;{top >> 16};{(top >> 8) & 255};{top & 255}m"
                    f"\x1b[48;2;{bottom >> 16};{(bottom >> 8) & 255};{bottom & 255}m▀"
                )
            lines.append("".join(cells) + "\x1b[0m")
        return "\n".join(lines)
