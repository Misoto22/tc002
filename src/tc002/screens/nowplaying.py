"""What is playing in Music or Spotify on this Mac: the title scrolling, the artist below.

Read with AppleScript (osascript), only from an app that is already running; macOS asks
once for permission to let tc002 talk to it. Nothing playing shows a quiet note.
"""

import subprocess
from dataclasses import dataclass

from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED
from . import ticker

SCRIPT = """
on playing(appName)
  if application appName is running then
    tell application appName
      if player state is playing then
        return (artist of current track) & tab & (name of current track)
      end if
    end tell
  end if
  return ""
end playing
set found to playing("Spotify")
if found is "" then set found to playing("Music")
return found
"""
NOTE = [".####", ".#..#", ".#..#", ".#..#", "##.##", "##.##", "....."]
TEXT_X = 8


def osascript(script):
    done = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, timeout=10, check=True
    )
    return done.stdout.strip()


@dataclass(frozen=True)
class State:
    title: str | None  # None: nothing playing
    artist: str = ""


class NowPlayingScreen:
    APP = "nowplaying"
    TICK = 10.0

    def __init__(self, options=None, run=osascript):
        self.run = run

    def sample(self):
        found = self.run(SCRIPT)
        if not found:
            return State(None)
        artist, _, title = found.partition("\t")
        return State(title, artist)

    def render(self, state):
        if state.title is None:
            c = Canvas()
            c.sprite(1, 4, NOTE, LED["gray"])
            c.text(TEXT_X + 2, 5, "NOT PLAYING", LED["gray"], big=False)
            return Animation.still(c, key=state)
        table = font.for_text(state.title)
        cjk = table not in (font.BIG, font.SMALL)
        table = table if cjk else font.SMALL
        artist = state.artist.upper()[:10]

        def static(c):
            c.sprite(1, 4, NOTE, LED["violet"])
            if not cjk:
                c.text(TEXT_X + 2, 9, artist, LED["label"], big=False)

        area = {"x0": TEXT_X, "width": WIDTH - TEXT_X}
        frames = ticker.frames(static, state.title, 2, LED["white"], table, **area)
        return Animation(frames, ticker.FRAME_MS, key=state)
