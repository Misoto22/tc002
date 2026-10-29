"""Live screens. Each class has APP, TICK, sample() -> state and render(state) -> Animation,
and optionally OPTIONS (see options.py) taken as `options=` when built."""

from . import options as screen_options
from .agenda import AgendaScreen
from .air import AirScreen
from .claude import ClaudeScreen
from .countdown import CountdownScreen
from .crypto import CryptoScreen
from .fire import FireScreen
from .focus import FocusScreen
from .github import GitHubScreen
from .hackernews import HackerNewsScreen
from .home import HomeScreen
from .life import LifeScreen
from .moon import MoonScreen
from .nowplaying import NowPlayingScreen
from .progress import ProgressScreen
from .stocks import StocksScreen
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
        AgendaScreen,
        GitHubScreen,
        NowPlayingScreen,
        AirScreen,
        CryptoScreen,
        StocksScreen,
        HackerNewsScreen,
        HomeScreen,
    )
}
# screens that read the internet or another app: never sampled just to draw a preview
NETWORKED = {"agenda", "github", "nowplaying", "air", "crypto", "stocks", "hackernews", "home"}
# screens that take their options in the constructor; where, from the weather city;
# connections (tokens, addresses), from the settings
_TAKES_OPTIONS = {"focus", "progress", "countdown", "worldclock", "sun", "moon", "life", "fire"}
_TAKES_OPTIONS |= NETWORKED
_LOCATED = {"sun", "air"}
_CONNECTED = {"agenda", "home"}


def build(name, settings=None):
    """A screen with its options from tc002.toml; the sun screen takes the weather city."""
    cls = SCREENS[name]
    if name not in _TAKES_OPTIONS:
        return cls()
    values = dict((settings.screen_options if settings else {}).get(name, {}))
    if name in _LOCATED and settings is not None:
        weather = settings.apps.get("weather", {})
        values.setdefault("lat", weather.get("lat"))
        values.setdefault("lon", weather.get("lon"))
    options = {**screen_options.resolved(cls, values), **values}
    if name in _CONNECTED:
        return cls(options=options, settings=settings)
    return cls(options=options)
