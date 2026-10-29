"""Fixed example states of every screen, for docs/screens/*.gif and the web UI's previews."""

import math

from . import claude, message, sysmon
from . import usage as usage_screen

_WAVE = tuple(int(40 + 28 * math.sin(i / 5) + 14 * math.sin(i / 1.7)) for i in range(52))


def examples():
    """name -> Animation, rendered fresh on each call."""
    return {
        "claude-busy": claude.ClaudeScreen().render(claude.State(3, 4, True)),
        "claude-idle": claude.ClaudeScreen().render(claude.State(2, 0, False)),
        "claude-off": claude.ClaudeScreen().render(claude.State(0, 0, False)),
        "claude-done": claude.ClaudeScreen().render(claude.State(1, 0, False, "done")),
        "claude-wait": claude.ClaudeScreen().render(claude.State(1, 0, False, "wait")),
        "sys": sysmon.SysScreen().render(sysmon.State(_WAVE[-1], 74, _WAVE)),
        "usage": usage_screen.render(
            usage_screen.State(
                (
                    usage_screen.Page("claude", 1_200_000, 340_000),
                    usage_screen.Page("codex", 860_000, 120_000, 23.0, 61.0),
                )
            )
        ),
        "text": message.text_animation("BUILD OK", "green")[0],
        "alert-error": message.alert_animation("FAILED", "error"),
    }
