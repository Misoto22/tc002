"""Fixed example states of every screen, for docs/screens/*.gif and the web UI's previews."""

import math

from . import claude, message, sysmon
from . import usage as usage_screen

_WAVE = tuple(int(40 + 28 * math.sin(i / 5) + 14 * math.sin(i / 1.7)) for i in range(52))


def examples():
    """name -> Animation, rendered fresh on each call."""
    return {
        "claude": claude.ClaudeScreen().render(claude.State(3, 1, 2)),
        "claude-idle": claude.ClaudeScreen().render(claude.State(0, 0, 0)),
        "claude-wait": claude.ClaudeScreen().render(claude.State(3, 1, 2, ("wait", "kura"))),
        "claude-done": claude.ClaudeScreen().render(claude.State(2, 0, 3, ("done", "moomoo"))),
        "sys": sysmon.SysScreen().render(sysmon.State(_WAVE[-1], 74, _WAVE)),
        "usage": usage_screen.render(
            usage_screen.State(
                (usage_screen.Row("claude", 62, 38), usage_screen.Row("codex", 14, 61))
            )
        ),
        "usage-unknown": usage_screen.render(
            usage_screen.State(
                (usage_screen.Row("claude", 97, 70), usage_screen.Row("codex", None, None))
            )
        ),
        "text": message.text_animation("BUILD OK", "green")[0],
        "alert-error": message.alert_animation("FAILED", "error"),
    }
