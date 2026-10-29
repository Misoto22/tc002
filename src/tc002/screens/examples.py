"""Fixed example states of every screen, for docs/screens/*.gif and the web UI's previews."""

import math

from . import (
    agenda,
    air,
    claude,
    countdown,
    crypto,
    fire,
    focus,
    github,
    hackernews,
    home,
    life,
    message,
    moon,
    nowplaying,
    progress,
    stocks,
    sun,
    sysmon,
    worldclock,
)
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
        "focus": focus.FocusScreen().render(focus.State("focus", 18 * 60 + 42, 25 * 60)),
        "progress": progress.ProgressScreen().render(progress.State(62, 41, 83)),
        "countdown": countdown.CountdownScreen().render(countdown.State(64, 0, "NEW YEAR")),
        "worldclock": worldclock.WorldClockScreen().render(
            worldclock.State((("LON", "09 41", 0), ("NEW", "04 41", 0)))
        ),
        "sun": sun.SunScreen().render(sun.State("06:12", "17:48", 58)),
        "moon": moon.MoonScreen().render(moon.State(2, 0.27, 58)),
        "life": life.LifeScreen().render(life.State(1)),
        "fire": fire.FireScreen().render(fire.State()),
        "agenda": agenda.AgendaScreen().render(agenda.State("10:30", 25, "Design review")),
        "github": github.GitHubScreen().render(github.State(2, 5, 12)),
        "nowplaying": nowplaying.NowPlayingScreen().render(
            nowplaying.State("Aruarian Dance", "Nujabes")
        ),
        "air": air.AirScreen().render(air.State(32, 8.4)),
        "crypto": crypto.CryptoScreen().render(
            crypto.State((("BTC", "79.8K", -1.9), ("ETH", "2410", 2.3)))
        ),
        "stocks": stocks.StocksScreen().render(
            stocks.State(
                "AAPL", 343.83, 1.2, tuple(340 + (i % 7) - i / 9 + i / 4 for i in range(52)), 339.8
            )
        ),
        "hackernews": hackernews.HackerNewsScreen().render(
            hackernews.State("Show HN: A pixel clock that shows your coding agents", 312)
        ),
        "home": home.HomeScreen().render(
            home.State((("LIVING ROOM", "21.5°C"), ("HUMIDITY", "48%")))
        ),
        "text": message.text_animation("BUILD OK", "green")[0],
        "alert-error": message.alert_animation("FAILED", "error"),
    }
