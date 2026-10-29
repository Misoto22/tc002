"""Small games played on the clock with the Mac's keyboard (see session.py).

A game has NAME, keys it uses, `step(pressed)` once per frame with the keys held or
tapped since the last frame, `draw(canvas)`, `score` and `over`. They are written for
tc002 from scratch.
"""

from .breakout import Breakout
from .pong import Pong
from .snake import Snake

GAMES = {g.NAME: g for g in (Breakout, Snake, Pong)}
