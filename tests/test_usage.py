"""Token usage readers (Claude Code transcripts, Codex rollouts and database) and the screen."""

import json
import sqlite3
import time

from tc002 import presets, usage
from tc002.render.anim import MAX_FRAMES
from tc002.screens import usage as usage_screen
from tc002.usage.claude import ClaudeUsage
from tc002.usage.codex import CodexUsage

NOW = time.time()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t))


def assistant(t, msg_id, req, tokens, **extra):
    return json.dumps(
        {
            "type": "assistant",
            "timestamp": iso(t),
            "requestId": req,
            "message": {
                "id": msg_id,
                "usage": {
                    "input_tokens": tokens,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            **extra,
        }
    )


def test_claude_counts_today_and_window_and_dedupes(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    f = proj / "s.jsonl"
    lines = [
        assistant(NOW - 60, "m1", "r1", 100),
        assistant(NOW - 60, "m1", "r1", 100),  # streamed duplicate
        assistant(NOW - 6 * 3600, "m2", "r2", 1000),  # outside the 5 h window
        json.dumps({"type": "user", "timestamp": iso(NOW), "message": {"content": "hi"}}),
        "{half-written",
    ]
    f.write_text("\n".join(lines) + "\n")
    reader = ClaudeUsage(str(tmp_path), clock=lambda: NOW)
    u = reader.collect()
    assert u.window == 100
    assert u.today in (100, 1100)  # 1100 unless six hours ago was before midnight
    with f.open("a") as out:  # appended later: read incrementally
        out.write(assistant(NOW - 30, "m3", "r3", 7) + "\n")
    assert reader.collect().window == 107


def test_codex_rollouts_give_tokens_and_allowance(tmp_path):
    day = tmp_path / "sessions" / "2026" / "10" / "29"
    day.mkdir(parents=True)
    events = [
        {
            "timestamp": iso(NOW - 100),
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"last_token_usage": {"total_tokens": 500}},
                "rate_limits": {
                    "primary": {"used_percent": 12.5},
                    "secondary": {"used_percent": 40},
                },
            },
        },
        {
            "timestamp": iso(NOW - 50),
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"last_token_usage": {"total_tokens": 250}},
                "rate_limits": {
                    "primary": {"used_percent": 14.0},
                    "secondary": {"used_percent": 41},
                },
            },
        },
    ]
    (day / "rollout-x.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    u = CodexUsage(str(tmp_path), clock=lambda: NOW).collect()
    assert (u.window, u.limit_5h, u.limit_week, u.source) == (750, 14.0, 41.0, "codex-rollouts")


def test_codex_falls_back_to_the_state_database(tmp_path):
    with sqlite3.connect(tmp_path / "state_5.sqlite") as db:
        db.execute("CREATE TABLE threads (tokens_used INTEGER, updated_at INTEGER)")
        db.executemany(
            "INSERT INTO threads VALUES (?, ?)", [(300, int(NOW - 60)), (999, int(NOW - 9 * 86400))]
        )
    u = CodexUsage(str(tmp_path), clock=lambda: NOW).collect()
    assert (u.window, u.source) == (300, "codex-database")


def test_codex_absent_is_none(tmp_path):
    assert CodexUsage(str(tmp_path / "missing")).collect().source == "none"


def test_short_and_rough():
    assert [usage.short(n) for n in (12, 8420, 84200, 1_234_567, 3_400_000_000)] == [
        "12",
        "8.4K",
        "84K",
        "1.2M",
        "3.4B",
    ]
    assert usage.rough(146_475_601) == 150_000_000 and usage.rough(42) == 42


def test_usage_screen_hides_codex_when_absent_and_fits_the_clock(tmp_path):
    class Fixed:
        def __init__(self, u):
            self.u = u

        def collect(self):
            return self.u

    screen = usage_screen.UsageScreen(
        Fixed(usage.Usage(1_234_567, 1000, source="x")), Fixed(usage.Usage(0, 0))
    )
    state = screen.sample()
    assert [p.agent for p in state.pages] == ["claude"]
    anim = screen.render(state)
    assert len(anim.frames) <= MAX_FRAMES
    anim.payload()


def test_presets_add_what_they_need():
    data = {"screens": {"enabled": ["claude"]}, "device": {"keep_builtins": []}}
    out = presets.apply(data, "developer")
    assert out["screens"]["enabled"] == ["claude", "usage", "sys"]
    assert out["device"]["keep_builtins"] == ["clock"]
    assert data["device"]["keep_builtins"] == []  # input untouched
