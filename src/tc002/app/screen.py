"""Use cases that change what is on the screen now, without touching tc002.toml:
switch, messages, screen off/on, the focus timer, games, the service in the foreground.

Messages come in two kinds on purpose: `send_text`/`send_alert` play and wait (a
script's `tc002 text` should return when the clock is done), `start_message` returns at
once and plays in the background (a UI or an agent should not block on the clock)."""

import threading
import time

from ..clock import builtins
from ..clock.device import DeviceError
from ..runtime import night
from ..runtime.game import Session
from ..runtime.output import Output
from ..screens import SCREENS, build, message
from ..state import focus as focus_timer
from . import catalog
from .errors import Conflict, InvalidRequest, InvalidSettings

FOCUS_MINUTES = (1, 180)
MESSAGE_HOLD = 10  # seconds a short message stays before it is removed


class OnScreen:
    # -- switching ----------------------------------------------------------------

    def show(self, screen=None, builtin=None):
        """Switch the clock to a live screen or a built-in app now. The rotation takes
        over again at its next slot."""
        dev = self.device()
        if screen:
            if screen not in SCREENS:
                raise InvalidRequest("Unknown screen", f"No screen named {screen!r}.")
            # The background service may not run this screen (yet): put one frame on the
            # clock first, so switching to it cannot fail with "app not found".
            if screen not in dev.apps():
                live = build(screen, self.settings_or_none())
                frames = live.render(live.sample())
                dev.push(screen, frames.payload(theme=self.led_theme()))
            dev.switch_custom(screen)
            return {"ok": True, "screen": screen}
        if builtin:
            try:
                app = builtins.lookup(builtin)
            except ValueError as exc:
                raise InvalidRequest("Unknown built-in app", str(exc)) from None
            dev.switch_builtin(app.category, app.index)
            return {"ok": True, "builtin": builtin}
        raise InvalidRequest("Nothing to show", "Send `screen` or `builtin`.")

    def remove_apps(self, names=None):
        """Remove custom apps from the clock (all of them when none are named)."""
        dev = self.device()
        names = list(names or dev.apps())
        for name in names:
            dev.remove(name)
        return names

    # -- messages -----------------------------------------------------------------

    def _target(self):
        """The clock, or None in preview mode (frames become GIFs in `self.preview_dir`)."""
        dev = None if self.preview_dir else self.device()
        return dev, Output(dev, self.preview_dir)

    def send_text(self, text, color="white", app="msg", passes=2, show=False):
        """Play text and wait for it. Short text stays; long text scrolls `passes` times
        and is then removed."""
        dev, out = self._target()
        segments = message.text_animation(text, color)
        if len(segments) == 1:
            out.show(app, segments[0])
        else:  # long text: segments back to back, then leave the clock clean
            for _ in range(max(1, passes)):
                for seg in segments:
                    out.show(app, seg)
                    if dev is None:
                        break
                    time.sleep(seg.duration_s())
            if dev is not None:
                out.remove(app)
                return {"app": app, "removed": True}
        if show and dev is not None:
            dev.switch_custom(app)
        return {"app": app, "removed": False}

    def send_alert(self, text, kind="done", color=None, app="alert", seconds=10, keep=False):
        """Show an alert and wait `seconds` before removing it, unless `keep`."""
        dev, out = self._target()
        out.show(app, message.alert_animation(text, kind, color))
        if dev is None:
            return {"app": app, "removed": False}
        dev.switch_custom(app)
        if not keep:
            time.sleep(seconds)
            out.remove(app)
        return {"app": app, "removed": not keep}

    def start_message(self, text, type="text", kind="done", color=None):
        """Text or alert, played in the background so the caller returns at once; the
        clock goes back to the rotation when it ends."""
        dev = self.device()
        text = str(text or "").strip()
        if not text:
            raise InvalidRequest("Empty message", "Type something to send.")
        if type == "alert":
            if kind not in catalog.ALERT_KINDS:
                choices = ", ".join(catalog.ALERT_KINDS)
                raise InvalidRequest("Unknown alert kind", f"Choose one of {choices}.")
            segments, app = [message.alert_animation(text, kind, color)], "alert"
        else:
            segments, app = message.text_animation(text, color or "white"), "msg"
        threading.Thread(target=_play, args=(dev, app, segments), daemon=True).start()
        return {"ok": True, "app": app, "seconds": round(sum(s.duration_s() for s in segments))}

    # -- night --------------------------------------------------------------------

    def screen_off(self, until_morning=False):
        """Screen fully dark now, until turned on (or until the night schedule's end)."""
        settings = self.settings_or_none()
        until = night.until_morning(settings) if until_morning else None
        return night.turn_off(self.device(), settings, until)

    def screen_on(self):
        """Light the screen now; inside the night schedule it stays lit until it ends."""
        return night.turn_on(self.device(), self.settings_or_none())

    # -- focus timer --------------------------------------------------------------

    def focus_start(self, minutes=None):
        settings = self.settings_or_none()
        screen = build("focus", settings)
        minutes = screen.minutes if minutes is None else minutes
        low, high = FOCUS_MINUTES
        if not isinstance(minutes, int) or isinstance(minutes, bool) or not low <= minutes <= high:
            raise InvalidSettings(
                "Invalid settings", f"Minutes must be a whole number from {low} to {high}."
            )
        focus_timer.start(minutes, screen.break_minutes)
        return {
            "running": True,
            "minutes": minutes,
            "break": screen.break_minutes,
            "screenEnabled": settings is not None and "focus" in settings.screens,
        }

    def focus_stop(self):
        focus_timer.stop()
        return {"running": False}

    # -- games --------------------------------------------------------------------

    def play_game(self, name):
        """Start a game on the clock (stopping the one running, if any)."""
        self.stop_game()
        if name not in catalog.GAME_KEYS:
            choices = ", ".join(catalog.GAME_KEYS)
            raise InvalidRequest("Invalid settings", f"Choose one of {choices}.")
        self._game = Session(self.device(), name, self.led_theme())
        self._game.start()
        return {"running": True, "game": name}

    def stop_game(self):
        game = getattr(self, "_game", None)
        if game is not None:
            game.stop()
            self._game = None
        return {"running": False}

    def game_key(self, key, down):
        game = getattr(self, "_game", None)
        if game is None:
            raise Conflict("Nothing to show", "No game is running.")
        if key not in catalog.GAME_KEYS[game.name]:
            return {"ignored": key}
        game.key(key, bool(down))
        return {"ok": True}

    def game_frame(self):
        game = getattr(self, "_game", None)
        return game.snapshot() if game else {"running": False}

    # -- the service, in the foreground ---------------------------------------------

    def watch(self, once=False):
        """Run the screens and the rotation in the foreground until stopped."""
        from ..runtime import watcher

        dev = None if (self.preview_dir or not self.host) else self.device()
        watcher.watch(dev, self.settings(), self.preview_dir, once=once)


def _play(dev, app, segments, hold=MESSAGE_HOLD):
    try:
        for seg in segments:
            dev.push(app, seg.payload())
            dev.switch_custom(app)
            time.sleep(max(seg.duration_s(), hold if len(segments) == 1 else 0))
        dev.remove(app)
    except DeviceError:
        pass  # best effort: the caller already reported the message as accepted
