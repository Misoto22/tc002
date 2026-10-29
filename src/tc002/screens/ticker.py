"""Text that does not fit scrolls through one GIF: shared by the screens with headlines.

A screen gets at most MAX_FRAMES frames per GIF, so a long line moves STEP pixels a
frame and the loop restarts from the right edge; text that fits stays still.
"""

from ..render import font
from ..render.anim import MAX_FRAMES
from ..render.canvas import WIDTH

STEP, FRAME_MS = 3, 110


def offsets(text, table, x0=0, width=WIDTH):
    """x positions, one per frame, for drawing `text` in the area x0..x0+width."""
    span = font.text_width(table, text)
    if span <= width:
        return [x0]
    path = list(range(x0 + width // 2, x0 - span, -STEP))  # from mid-area to fully out
    return path[:MAX_FRAMES]


def frames(draw_static, text, y, colour, table, x0=0, width=WIDTH):
    """Canvases: `draw_static(canvas)` for the fixed parts, `text` scrolling at row `y`."""
    from ..render.canvas import Canvas

    out = []
    for x in offsets(text, table, x0, width):
        c = Canvas()
        c.text(x, y, text, colour, table=table)
        if x0:  # keep the scrolling text out of the fixed area on its left
            c.rect(0, y, x0, font.height(table), 0)
        draw_static(c)
        out.append(c)
    return out
