"""Screens that read services: parsing their data (faked), the Keychain wrapper, and
connection settings. Nothing here touches the network, the Keychain or another app."""

import datetime as dt
import subprocess
from zoneinfo import ZoneInfo

import pytest

from tc002 import config, connections, keychain
from tc002.screens import (
    NETWORKED,
    agenda,
    air,
    build,
    crypto,
    github,
    hackernews,
    home,
    nowplaying,
    stocks,
)


def fits(screen):
    anim = screen.render(screen.sample())
    anim.payload()
    return anim


def test_air_quality_bands_and_no_city():
    screen = air.AirScreen(
        {"lat": "1", "lon": "2"},
        get=lambda url: {"current": {"european_aqi": 73.4, "pm2_5": 45.25}},
    )
    assert screen.sample() == air.State(73, 45.2) and air.band(73) == "amber"
    fits(screen)
    assert air.AirScreen().sample().aqi is None


def test_crypto_change_since_open_and_short_prices():
    stats = {
        "BTC-USD": {"open": "100000", "last": "98000"},
        "ETH-USD": {"open": "2000", "last": "2100"},
    }
    screen = crypto.CryptoScreen(get=lambda url: stats[url.split("/")[-2]])
    assert screen.sample().rows == (("BTC", "98.0K", -2.0), ("ETH", "2100", 5.0))
    fits(screen)


def test_stocks_chart_against_yesterdays_close():
    reply = {
        "chart": {
            "result": [
                {
                    "meta": {"regularMarketPrice": 110.0, "chartPreviousClose": 100.0},
                    "indicators": {"quote": [{"close": [100, None, 105, 110]}]},
                }
            ]
        }
    }
    clock = [0.0]
    screen = stocks.StocksScreen(
        {"symbols": ["msft", "0700.HK"], "seconds": 8, "refresh": 5},
        get=lambda url: reply,
        clock=lambda: clock[0],
    )
    state = screen.sample()
    assert (state.quote.symbol, state.quote.change, state.quote.points) == (
        "MSFT",
        10.0,
        (100, 105, 110),
    )
    assert (state.index, state.count) == (0, 2)
    clock[0] = 8.0  # the next symbol after `seconds`, from the same fetch
    assert screen.sample().quote.symbol == "0700.HK"
    fits(screen)


def test_stock_price_never_runs_into_the_change():
    from tc002.render import font

    for price in (343.83, 1234.5, 98765.4, 0.42):
        quote = stocks.Quote("BRK-B", price, -12.3, (1, 2, 3), 2)
        c = stocks.StocksScreen().render(stocks.State(quote, 0, 4)).frames[0]
        change_x = 52 - font.text_width(font.SMALL, "-12.3")
        lit = {
            x
            for x in range(change_x - stocks.GAP, change_x)
            if any(c.px[y * 52 + x] for y in range(5))
        }
        assert not lit, f"{price}: price touches the change"


def _hn(items, kind="top"):
    def get(url):
        if url.endswith(f"{kind}stories.json"):
            return list(items)
        return items[int(url.rsplit("/", 1)[1].removesuffix(".json"))]

    return get


def test_hacker_news_filters_and_cycles_stories():
    items = {
        1: {
            "title": "A very long headline about something that matters",
            "score": 312,
            "descendants": 87,
        },
        2: {"title": "Too small", "score": 4},
        3: {"title": "Dead", "score": 999, "dead": True},
        4: {"title": "Rust in the kernel", "score": 150, "descendants": 3},
    }
    clock = [0.0]
    screen = hackernews.HackerNewsScreen(
        {"count": 5, "min_points": 100, "seconds": 10}, get=_hn(items), clock=lambda: clock[0]
    )
    first = screen.sample()
    assert (first.story.points, first.story.comments, first.count) == (312, 87, 2)
    clock[0] = 10.0
    assert screen.sample().story.title == "Rust in the kernel"
    anim = fits(screen)
    assert len(anim.frames) >= 1
    rust = hackernews.HackerNewsScreen({"keyword": "RUST"}, get=_hn(items))
    assert rust.sample().story.title == "Rust in the kernel"


def test_hacker_news_new_list_ignores_points_and_empty_is_an_error():
    items = {7: {"title": "Just posted", "score": 1}}
    assert (
        hackernews.HackerNewsScreen({"list": "new"}, get=_hn(items, "new")).sample().story.points
        == 1
    )
    with pytest.raises(ValueError, match="no story"):
        hackernews.HackerNewsScreen({"min_points": 500}, get=_hn(items)).sample()


def test_now_playing_and_nothing_playing():
    playing = nowplaying.NowPlayingScreen(run=lambda script: "Nujabes\tAruarian Dance")
    assert playing.sample() == nowplaying.State("Aruarian Dance", "Nujabes")
    fits(playing)
    assert nowplaying.NowPlayingScreen(run=lambda script: "").sample().title is None


def test_github_counts_from_gh():
    answers = {"reviews": 2, "mine": 5, "unread": 150}
    screen = github.GitHubScreen(
        run=lambda args: next(v for k, v in answers.items() if args == github.QUERIES[k])
    )
    assert screen.sample() == github.State(2, 5, 150)
    fits(screen)


ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=Europe/London:20270104T093000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR
SUMMARY:Standup\\, team
END:VEVENT
BEGIN:VEVENT
DTSTART:20270106T080000Z
SUMMARY:Dentist
END:VEVENT
END:VCALENDAR
"""


def test_agenda_finds_the_next_occurrence_of_a_weekly_event():
    now = dt.datetime(2027, 1, 6, 8, 30, tzinfo=ZoneInfo("Europe/London"))  # Wednesday
    when, title = agenda.next_event(ICS, now)
    assert title == "Standup, team" and when.hour == 9 and when.day == 6


def test_agenda_needs_a_connection_and_reads_the_keychain(monkeypatch):
    assert agenda.AgendaScreen(settings=config.parse({})).sample().connected is False
    monkeypatch.setattr(connections, "value", lambda s, c, f: "https://cal.example/private.ics")
    now = dt.datetime(2027, 1, 6, 7, 0, tzinfo=dt.UTC)
    screen = agenda.AgendaScreen(settings=None, get=lambda url: ICS.encode(), clock=lambda: now)
    assert screen.sample() == agenda.State("08:00", 60, "Dentist")
    fits(screen)


def test_home_assistant_reads_all_states_once_and_pages(monkeypatch):
    values = {("homeassistant", "url"): "http://ha:8123", ("homeassistant", "token"): "tok"}
    monkeypatch.setattr(connections, "value", lambda s, c, f: values[(c, f)])
    seen = []
    states = [
        {
            "entity_id": "sensor.den",
            "state": "21.54",
            "attributes": {
                "friendly_name": "Den",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
            },
        },
        {
            "entity_id": "binary_sensor.front",
            "state": "on",
            "attributes": {"friendly_name": "Front door", "device_class": "door"},
        },
        {
            "entity_id": "person.henry",
            "state": "not_home",
            "attributes": {"friendly_name": "Henry"},
        },
        {"entity_id": "automation.x", "state": "on", "attributes": {}},
    ]

    def get(url, headers):
        seen.append((url, headers))
        return states

    clock = [0.0]
    screen = home.HomeScreen(
        {
            "entities": ["sensor.den", "binary_sensor.front", "person.henry", "sensor.gone"],
            "seconds": 5,
        },
        settings=None,
        get=get,
        clock=lambda: clock[0],
    )
    shown = []
    for t in (0, 5, 10, 15):
        clock[0] = t
        v = screen.sample().value
        shown.append((v.name, v.text))
    assert shown == [("DEN", "21.5C"), ("FRONT DOOR", "OPEN"), ("HENRY", "AWAY"), ("GONE", "--")]
    assert seen == [("http://ha:8123/api/states", {"Authorization": "Bearer tok"})]  # one call
    fits(screen)
    picker = home.entity_list(states)
    assert [e["id"] for e in picker] == ["sensor.den", "binary_sensor.front", "person.henry"]


def test_home_assistant_without_a_connection(monkeypatch):
    monkeypatch.setattr(connections, "value", lambda s, c, f: None)
    assert home.HomeScreen(settings=None).sample().connected is False


class FakeSecurity:
    def __init__(self):
        self.store, self.calls = {}, []

    def __call__(self, args, input=None, **kwargs):
        self.calls.append((args, input))
        if args[:2] == ["security", "-i"]:
            account = input.split(" -a ")[1].split('"')[1]
            self.store[account] = input.split(" -w ")[1].strip().strip('"')
            return subprocess.CompletedProcess(args, 0, "", "")
        account = args[args.index("-a") + 1]
        if args[1] == "delete-generic-password":
            self.store.pop(account, None)
            return subprocess.CompletedProcess(args, 0, "", "")
        if account not in self.store:
            return subprocess.CompletedProcess(args, 44, "", "not found")
        return subprocess.CompletedProcess(args, 0, self.store[account] + "\n", "")


def test_keychain_values_never_appear_on_a_command_line():
    fake = FakeSecurity()
    keychain.save("calendar.ics_url", "https://secret.example/cal.ics", run=fake)
    assert keychain.get("calendar.ics_url", run=fake) == "https://secret.example/cal.ics"
    assert all("secret.example" not in " ".join(args) for args, _ in fake.calls)
    keychain.delete("calendar.ics_url", run=fake)
    assert keychain.get("calendar.ics_url", run=fake) is None
    with pytest.raises(ValueError):
        keychain.save("x", "two\nlines", run=fake)


def test_connections_keep_secrets_out_of_tc002_toml():
    assert config.parse({"connections": {"homeassistant": {"url": "http://ha"}}}).connections
    for bad in ({"homeassistant": {"token": "x"}}, {"nosuch": {}}):
        with pytest.raises(config.ConfigError):
            config.parse({"connections": bad})


def test_networked_screens_are_never_sampled_for_previews():
    from tc002.web import api

    assert NETWORKED.isdisjoint(api.LIVE_SCREENS)
    assert {build(n).APP for n in NETWORKED} == NETWORKED


def test_without_a_keychain_nothing_is_saved_and_saving_says_so():
    def missing(*args, **kwargs):
        raise FileNotFoundError("security")

    assert keychain.get("x", run=missing) is None and not keychain.has("x", run=missing)
    with pytest.raises(OSError):
        keychain.save("x", "value", run=missing)
