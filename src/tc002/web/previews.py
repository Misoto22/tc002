"""LED previews the UI shows: example screens, live screens, built-in apps, games and
message drafts, each as a mock-up GIF.

Example screens, built-in apps and games are fixed pictures, so each is drawn once per
LED theme and kept (`_fixed`): a page full of thumbnails then loads at once instead of
re-rendering every example on each request.
"""

from functools import lru_cache

from ..games import GAMES
from ..games.demo import demo
from ..render import mockup, themes
from ..screens import NETWORKED, SCREENS, build, builtin_previews, message
from ..screens.examples import examples
from .errors import ApiError

# cheap, local and quiet to sample, so previewed with real data
LIVE_SCREENS = set(SCREENS) - {"sys"} - NETWORKED


class Previews:
    def preview(self, name, query):
        """LED mock-up GIF bytes for an example screen or a message draft.

        Screens are drawn in the saved LED theme, or in `?theme=` (a draft not yet saved);
        messages keep the colour they were given.
        """
        theme = query.get("theme") if query.get("theme") in themes.THEMES else None
        theme = theme or self._led_theme()
        if name == "text":
            anim, theme = (
                message.text_animation(
                    query.get("text", "TEXT")[: message.MAX_CHARS], query.get("color", "white")
                )[0],
                themes.CLASSIC,
            )
        elif name == "alert":
            anim = message.alert_animation(
                query.get("text", "DONE")[: message.ALERT_MAX_CHARS],
                query.get("kind", "done"),
                query.get("color"),
            )
            theme = themes.CLASSIC
        elif name.removeprefix("live-") in LIVE_SCREENS and name.startswith("live-"):
            screen = build(name.removeprefix("live-"), self._settings_or_none())
            anim = screen.render(screen.sample())
        else:
            gif = _fixed(name, theme)
            if gif is None:
                raise ApiError(404, "Unknown preview", f"No preview named {name!r}.")
            return gif
        return mockup.led_gif(anim, theme)


@lru_cache(maxsize=1)
def _examples():
    return examples()


@lru_cache(maxsize=512)
def _fixed(name, theme):
    """GIF bytes of an example screen, a built-in app or a game demo; None if unknown."""
    if name.startswith("game-") and name.removeprefix("game-") in GAMES:
        anim = demo(name.removeprefix("game-"))
    elif name.startswith("builtin-"):
        try:
            anim = builtin_previews.render(name.removeprefix("builtin-"))
        except ValueError:
            return None
    elif name in _examples():
        anim = _examples()[name]
    else:
        return None
    return mockup.led_gif(anim, theme)
