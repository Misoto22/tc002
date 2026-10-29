"""LED previews the UI shows: example screens, live screens, built-in apps, games and
message drafts, each as a mock-up GIF."""

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
        elif name.startswith("game-") and name.removeprefix("game-") in GAMES:
            anim = demo(name.removeprefix("game-"))
        elif name.startswith("builtin-"):
            try:
                anim = builtin_previews.render(name.removeprefix("builtin-"))
            except ValueError:
                raise ApiError(404, "Unknown preview", f"No built-in app {name!r}.") from None
        else:
            anims = examples()
            if name not in anims:
                raise ApiError(404, "Unknown preview", f"No preview named {name!r}.")
            anim = anims[name]
        return mockup.led_gif(anim, theme)
