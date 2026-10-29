"""Regenerate docs/screens/*.gif: LED mock-ups of every screen in fixed example states,
and of each game playing itself.

usage: uv run python scripts/render_docs.py
"""

from pathlib import Path

from tc002.games import GAMES
from tc002.games.demo import demo
from tc002.render import mockup
from tc002.screens.examples import examples

OUT = Path(__file__).resolve().parent.parent / "docs" / "screens"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.gif"):
        old.unlink()
    for name, anim in examples().items():
        anim.payload()  # same firmware limits as a real push
        (OUT / f"{name}.gif").write_bytes(mockup.led_gif(anim))
        print(f"docs/screens/{name}.gif  {len(anim.frames)} frames")
    for name in GAMES:  # streamed frame by frame on the clock, so no payload limits apply
        anim = demo(name)
        (OUT / f"game-{name}.gif").write_bytes(mockup.led_gif(anim))
        print(f"docs/screens/game-{name}.gif  {len(anim.frames)} frames")


if __name__ == "__main__":
    main()
