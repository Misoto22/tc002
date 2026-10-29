"""Live screens. Each class has APP, TICK, sample() -> state and render(state) -> Animation."""

from .claude import ClaudeScreen
from .sysmon import SysScreen

SCREENS = {"claude": ClaudeScreen, "sys": SysScreen}
