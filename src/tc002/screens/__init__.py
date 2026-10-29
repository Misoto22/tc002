"""Live screens. Each class has APP, TICK, sample() -> state and render(state) -> Animation,
and optionally OPTIONS (see options.py) taken as `options=` when built."""

from . import options as screen_options
from .claude import ClaudeScreen
from .countdown import CountdownScreen
from .fire import FireScreen
from .focus import FocusScreen
from .life import LifeScreen
from .moon import MoonScreen
from .progress import ProgressScreen
from .sun import SunScreen
from .sysmon import SysScreen
from .usage import UsageScreen
from .worldclock import WorldClockScreen

SCREENS = {
    cls.APP: cls
    for cls in (
        ClaudeScreen,
        UsageScreen,
        SysScreen,
        FocusScreen,
        ProgressScreen,
        CountdownScreen,
        WorldClockScreen,
        SunScreen,
        MoonScreen,
        LifeScreen,
        FireScreen,
    )
}
# screens that take their options in the constructor
_TAKES_OPTIONS = {"focus", "progress", "countdown", "worldclock", "sun", "moon", "life", "fire"}


def build(name, settings=None):
    """A screen with its options from tc002.toml; the sun screen takes the weather city."""
    cls = SCREENS[name]
    if name not in _TAKES_OPTIONS:
        return cls()
    values = dict((settings.screen_options if settings else {}).get(name, {}))
    if name == "sun" and settings is not None:
        weather = settings.apps.get("weather", {})
        values.setdefault("lat", weather.get("lat"))
        values.setdefault("lon", weather.get("lon"))
    return cls(options={**screen_options.resolved(cls, values), **values})
