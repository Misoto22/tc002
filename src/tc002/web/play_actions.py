"""API actions for things you play with on the clock: the games and the focus timer.

Mixed into web.api.Api."""

from ..games import GAMES
from ..games.session import Session
from ..screens import build
from .errors import ApiError


class PlayActions:
    def play(self, body):
        """Start a game on the clock, or stop the one running."""
        if self.game is not None:
            self.game.stop()
            self.game = None
        if body.get("action") == "stop":
            return {"running": False}
        name = body.get("game")
        if name not in GAMES:
            raise ApiError(422, "Invalid settings", f"Choose one of {', '.join(GAMES)}.")
        self.game = Session(self._device(), name, self._led_theme())
        self.game.start()
        return {"running": True, "game": name}

    def game_key(self, body):
        if self.game is None:
            raise ApiError(409, "Nothing to show", "No game is running.")
        key = body.get("key")
        if key not in GAMES[self.game.name].KEYS:
            return {"ignored": key}
        self.game.key(key, bool(body.get("down")))
        return {"ok": True}

    def game_frame(self, query=None):
        return self.game.snapshot() if self.game else {"running": False}

    def focus(self, body):
        """Start or stop the focus timer screen."""
        from ..runtime import focus as timer

        if body.get("action") == "stop":
            timer.stop()
            return {"running": False}
        screen = build("focus", self._settings_or_none())
        minutes = body.get("minutes") or screen.minutes
        if not isinstance(minutes, int) or not 1 <= minutes <= 180:
            raise ApiError(422, "Invalid settings", "Minutes must be a whole number from 1 to 180.")
        timer.start(minutes, screen.break_minutes)
        return {"running": True, "minutes": minutes, "break": screen.break_minutes}


def _focus_now():
    from ..runtime import focus as timer

    now = timer.current()
    return {"phase": now[0], "left": round(now[1])} if now else None
