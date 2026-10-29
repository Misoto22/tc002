"""The keyboard games: rules, drawing within the board, and the session loop."""

import random
import threading

import pytest

from tc002.games import GAMES, Breakout, Pong, Snake
from tc002.games import session as game_session
from tc002.render.canvas import Canvas


def play(game, steps, keys=()):
    for _ in range(steps):
        game.step(set(keys))


@pytest.mark.parametrize("name", list(GAMES))
def test_every_game_draws_and_survives_random_keys(name):
    game = GAMES[name](random.Random(1))
    rng = random.Random(2)
    for _ in range(400):
        game.step({rng.choice(game.KEYS)})
        c = Canvas()
        game.draw(c)  # Canvas clips, so drawing must simply not raise
    assert isinstance(game.score, int)


def test_snake_grows_on_food_and_never_reverses():
    s = Snake(random.Random(0))
    s.food = (s.body[0][0] + 1, s.body[0][1])
    play(s, 2)
    assert s.score == 1 and len(s.body) == 4
    s.step({"left"})  # straight back into the neck: ignored
    assert s.heading == (1, 0)


def test_snake_dies_on_itself():
    s = Snake(random.Random(0))
    s.body = [(5, 5), (6, 5), (6, 6), (5, 6), (4, 6)]
    s.heading = (0, 1)
    play(s, 2)
    assert s.over


def test_breakout_bricks_score_and_a_missed_ball_costs_a_life():
    b = Breakout(random.Random(0))
    total = len(b.bricks)
    b.ball, b.vel = [10, 6], [0, -1]
    play(b, 2)
    assert b.score == 1 and len(b.bricks) == total - 1
    b.ball, b.vel, b.paddle = [0, 14], [0, 1], 40
    b.step(set())
    assert b.lives == 2


def test_pong_is_won_at_five():
    p = Pong(random.Random(0))
    p.points = [4, 0]
    p.ball, p.vel = [50, 8], [1, 0]
    p.it = 0  # the clock's paddle is far away
    play(p, 3)
    assert p.over and p.points[0] == 5


class Clock:
    def __init__(self):
        self.pushed, self.switched, self.removed = [], [], []

    def push(self, app, body):
        self.pushed.append(body)

    def switch_custom(self, app):
        self.switched.append(app)

    def remove(self, app):
        self.removed.append(app)


def test_session_pushes_bitmaps_holds_the_rotation_and_cleans_up(monkeypatch):
    from tc002.runtime import hold

    monkeypatch.setattr(game_session, "FRAME_MS", 5)
    clock = Clock()
    s = game_session.Session(clock, "snake")
    t = threading.Thread(target=s.run)
    t.start()
    s.key("up", True)
    while len(clock.pushed) < 5:
        pass
    assert hold.active() > 0  # the rotation keeps its hands off while a game runs
    s.stop()
    t.join(2)
    (db,) = clock.pushed[0]["draw"][0].values()
    assert db[:4] == [0, 0, 52, 16] and len(db[4]) == 52 * 16
    assert clock.switched == [game_session.APP] and clock.removed == [game_session.APP]
    assert hold.active() == 0 and not s.running
    with pytest.raises(ValueError):
        game_session.Session(clock, "tetris")
