"""API actions for things you play with on the clock: the games and the focus timer.

Mixed into web.api.Api."""

from ..games import GAMES
from ..games.session import Session
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
        self.game = Session(self.app.device(), name, self._led_theme())
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
        if body.get("action") == "stop":
            return self.app.focus_stop()
        result = self.app.focus_start(body.get("minutes") or None)
        return {k: result[k] for k in ("running", "minutes", "break")}
