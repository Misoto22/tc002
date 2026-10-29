"""The no-API screens: what each computes, that each fits the clock, and their options."""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from tc002 import config
from tc002.runtime import focus as timer
from tc002.screens import SCREENS, build, countdown, focus, moon, progress, sun, worldclock
from tc002.screens.examples import examples

NEW = ["focus", "progress", "countdown", "worldclock", "sun", "moon", "life", "fire"]


@pytest.mark.parametrize("name", NEW)
def test_every_new_screen_samples_renders_and_fits(name):
    screen = build(name)
    anim = screen.render(screen.sample())
    anim.payload()  # raises when over the firmware's frame or size limits
    examples()[name].payload()


def test_progress_of_a_known_moment():
    noon_wed = dt.datetime(2027, 7, 7, 12, 0)  # a Wednesday
    day, week, year = progress.fractions(noon_wed)
    assert day == 0.5 and week == pytest.approx(2.5 / 7) and 0.5 < year < 0.52


def test_countdown_days_then_hours_and_no_date():
    at = lambda s: lambda: dt.datetime.fromisoformat(s)  # noqa: E731
    days = countdown.CountdownScreen(
        {"date": "2027-01-01", "label": "new year"}, at("2026-12-29T12:00")
    )
    assert days.sample() == countdown.State(2, 720, "NEW YEAR")
    today = countdown.CountdownScreen({"date": "2027-01-01"}, at("2026-12-31T22:30"))
    assert today.sample() == countdown.State(0, 90, "")
    assert countdown.CountdownScreen().sample().days is None


def test_world_clock_tags_and_day_offsets():
    here = dt.datetime(2027, 1, 1, 5, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    screen = worldclock.WorldClockScreen(
        {"zones": ["Australia/Sydney", "America/New_York"]}, lambda: here
    )
    assert screen.sample().rows == (("SYD", "08 30", 0), ("NEW", "16 30", -1))


def test_sunrise_and_sunset_are_about_right():
    tz = ZoneInfo("Europe/London")
    rise, sunset = sun.sun_times(dt.date(2027, 6, 21), 51.5, -0.13, tz)
    assert (rise.hour, sunset.hour) == (4, 21)  # 04:43 and 21:21 in London at midsummer
    assert sun.sun_times(dt.date(2027, 6, 21), 78.2, 15.6, tz) is None  # Svalbard: no night


def test_sun_screen_takes_the_weather_city():
    settings = config.parse(
        {"apps": {"weather": {"city": "London", "lat": "51.5", "lon": "-0.13"}}}
    )
    assert build("sun", settings).lat == "51.5"
    assert build("sun").sample().rise is None  # no city: it asks for one


def test_moon_phase_of_a_known_full_moon():
    full = dt.datetime(2000, 1, 21, 4, 40, tzinfo=dt.UTC)
    state = moon.MoonScreen(clock=lambda: full).sample()
    assert state.eighth == 4 and state.lit > 95


def test_focus_timer_runs_focus_then_break_then_stops(tmp_path):
    path = tmp_path / "focus.json"
    t0 = 1_800_000_000.0
    timer.start(25, 5, path, now=t0)
    screen = focus.FocusScreen(clock=lambda: t0 + 60, path=path)
    assert screen.sample() == focus.State("focus", 24 * 60, 25 * 60)
    running = screen.render(screen.sample())
    assert len(running.frames) == 50 and running.delays()[0] == 1000  # ticks each second
    assert timer.current(path, t0 + 26 * 60)[0] == "break"
    assert timer.current(path, t0 + 31 * 60) is None and not path.exists()


def test_screen_options_are_validated_and_written_back(tmp_path):
    data = {"screen": {"countdown": {"date": "2027-01-01", "label": "NEW YEAR"}}}
    assert config.parse(data).screen_options["countdown"]["label"] == "NEW YEAR"
    for bad in (
        {"countdown": {"date": "next friday"}},
        {"worldclock": {"zones": ["Mars/Base"]}},
        {"focus": {"minutes": 500}},
        {"nosuch": {}},
    ):
        with pytest.raises(config.ConfigError):
            config.parse({"screen": bad})
    assert set(NEW) <= set(SCREENS)
