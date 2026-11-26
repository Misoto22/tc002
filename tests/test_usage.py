"""Token usage readers (Claude Code transcripts, Codex rollouts and database) and the screen."""

import json
import sqlite3
import time

from tc002 import usage
from tc002.config import presets
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


def test_usage_screen_rounds_limits_and_fits_the_clock(tmp_path):
    class Fixed:
        def __init__(self, u):
            self.u = u

        def collect(self):
            return self.u

    screen = usage_screen.UsageScreen(
        Fixed(usage.Usage(1_234_567, 1000, 62.4, 38.6, source="x")), Fixed(usage.Usage(0, 0))
    )
    state = screen.sample()
    assert state.rows == (usage_screen.Row("claude", 62, 39), usage_screen.Row("codex", None, None))
    anim = screen.render(state)
    assert len(anim.frames) <= MAX_FRAMES
    anim.payload()


def test_presets_add_what_they_need():
    data = {"screens": {"enabled": ["claude"]}, "device": {"keep_builtins": []}}
    out = presets.apply(data, "developer")
    assert out["screens"]["enabled"] == ["claude", "usage", "sys"]
    assert out["device"]["keep_builtins"] == ["clock"]
    assert data["device"]["keep_builtins"] == []  # input untouched


def status_reply(*models):
    return {
        "userStatus": {
            "cascadeModelConfigData": {
                "clientModelConfigs": [
                    {"label": label, "quotaInfo": info} for label, info in models
                ]
            }
        }
    }


def test_gemini_quota_takes_the_most_used_gemini_model():
    from tc002.usage import gemini

    reply = status_reply(
        ("Gemini 4 Neon (High)", {"remainingFraction": 0.98, "resetTime": iso(NOW + 3600)}),
        ("Gemini 3.8 Flash (Low)", {"remainingFraction": 0.5, "resetTime": iso(NOW + 3600)}),
        ("Claude Opus 5.5 (High)", {"resetTime": iso(NOW + 3600)}),  # exhausted: not Gemini
    )
    used, resets = gemini.quota(reply)
    assert used == 50.0 and abs(resets - round(NOW + 3600)) <= 1
    # an exhausted allowance omits remainingFraction (proto3 drops zeros)
    gone = status_reply(("Gemini 4 Neon (High)", {"resetTime": iso(NOW + 3600)}))
    assert gemini.quota(gone)[0] == 100.0
    assert gemini.quota({"unexpected": True}) is None


def test_gemini_reset_time_picks_the_window(tmp_path):
    from tc002.usage import gemini, limits

    path = tmp_path / "g.json"
    gemini.record((40.0, NOW + 2 * 3600), path, NOW)
    assert limits.latest(path, NOW) == {"limit_5h": 40.0, "reset_5h": NOW + 2 * 3600}
    gemini.record((100.0, NOW + 3 * 86400), path, NOW)  # the weekly cap binds now
    assert limits.latest(path, NOW) == {"limit_week": 100.0, "reset_week": NOW + 3 * 86400}
    # once the 5-hour window refills it comes back; the weekly reading is kept
    gemini.record((5.0, NOW + 4 * 3600), path, NOW)
    assert limits.latest(path, NOW)["limit_week"] == 100.0
    assert limits.latest(path, NOW)["limit_5h"] == 5.0


def test_gemini_reader_asks_the_local_server(tmp_path, monkeypatch):
    from tc002.usage import gemini

    daemon = tmp_path / "daemon"
    daemon.mkdir()
    (daemon / "hub_1.json").write_text(json.dumps({"httpPort": 1, "csrfToken": "t"}))
    asked = []

    def fake_fetch(port, token):
        asked.append((port, token))
        return status_reply(
            ("Gemini 4 Neon (High)", {"remainingFraction": 0.75, "resetTime": iso(NOW + 600)})
        )

    monkeypatch.setattr(gemini, "fetch", fake_fetch)
    reader = gemini.GeminiUsage(str(daemon), tmp_path / "g.json", clock=lambda: NOW)
    u = reader.collect()
    assert asked == [(1, "t")]
    assert u.source == "antigravity" and u.limit_5h == 25.0 and u.limit_week is None
    reader.collect()
    assert len(asked) == 1  # within REFRESH: the saved reading is used
    absent = gemini.GeminiUsage(str(tmp_path / "none"), tmp_path / "n.json", clock=lambda: NOW)
    assert absent.collect().source == "none"


def test_usage_screen_pages_three_agents():
    class Fixed:
        def __init__(self, u):
            self.u = u

        def collect(self):
            return self.u

    seen = usage.Usage(0, 0, 97.0, 10.0, source="x")
    screen = usage_screen.UsageScreen(Fixed(seen), Fixed(seen), Fixed(seen))
    state = screen.sample()
    assert [r.agent for r in state.rows] == ["claude", "codex", "gemini"]
    anim = screen.render(state)
    assert len(anim.frames) <= MAX_FRAMES  # both pages blink and still fit
    anim.payload()
    # Gemini without Codex shares the first page with Claude Code
    alone = usage_screen.UsageScreen(Fixed(seen), Fixed(usage.Usage(0, 0)), Fixed(seen))
    assert [r.agent for r in alone.sample().rows] == ["claude", "gemini"]
