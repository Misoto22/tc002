"""Regenerate docs/screens/*.gif: LED mock-ups of every screen in fixed example states.

usage: uv run python scripts/render_docs.py
"""

import math
from pathlib import Path

from tc002.render import mockup
from tc002.screens import claude, message, sysmon

OUT = Path(__file__).resolve().parent.parent / "docs" / "screens"
WAVE = tuple(int(40 + 28 * math.sin(i / 5) + 14 * math.sin(i / 1.7)) for i in range(52))

EXAMPLES = {
    "claude-busy": claude.ClaudeScreen().render(claude.State(3, 4, True)),
    "claude-idle": claude.ClaudeScreen().render(claude.State(2, 0, False)),
    "claude-off": claude.ClaudeScreen().render(claude.State(0, 0, False)),
    "claude-done": claude.ClaudeScreen().render(claude.State(1, 0, False, "done")),
    "claude-wait": claude.ClaudeScreen().render(claude.State(1, 0, False, "wait")),
    "sys": sysmon.SysScreen().render(sysmon.State(WAVE[-1], 74, WAVE)),
    "text": message.text_animation("BUILD OK", "green")[0],
    "alert-error": message.alert_animation("FAILED", "error"),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.gif"):
        old.unlink()
    for name, anim in EXAMPLES.items():
        anim.payload()  # same firmware limits as a real push
        (OUT / f"{name}.gif").write_bytes(mockup.led_gif(anim))
        print(f"docs/screens/{name}.gif  {len(anim.frames)} frames")


if __name__ == "__main__":
    main()
