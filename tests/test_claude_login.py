"""Claude limits fetched with Claude Code's stored login: token choice, saving, failures."""

import json
import urllib.error

from tc002.usage import claude_login, limits

NOW = 1_800_000_000.0
REPLY = {
    "five_hour": {"utilization": 41.0, "resets_at": "2027-01-15T10:00:00+00:00"},
    "seven_day": {"utilization": 12.5, "resets_at": "2027-01-20T10:00:00+00:00"},
}


def logins(monkeypatch, *docs):
    monkeypatch.setattr(claude_login, "_logins", lambda: iter(docs))


def oauth(token, expires=0):
    return {"claudeAiOauth": {"accessToken": token, "expiresAt": expires}}


def test_an_empty_keychain_token_falls_through_to_the_next_login(monkeypatch):
    logins(monkeypatch, oauth(""), oauth("tok-b", (NOW + 3600) * 1000))
    assert claude_login.access_token(NOW) == "tok-b"


def test_expired_tokens_are_not_used_in_seconds_or_milliseconds(monkeypatch):
    logins(monkeypatch, oauth("a", NOW - 10), oauth("b", (NOW - 10) * 1000))
    assert claude_login.access_token(NOW) is None


def test_a_due_refresh_saves_the_percentages(monkeypatch, tmp_path):
    logins(monkeypatch, oauth("tok"))
    seen = {}
    monkeypatch.setattr(claude_login, "fetch", lambda token: seen.setdefault("t", token) and REPLY)
    path = tmp_path / "l.json"
    assert claude_login.refresh_if_due(NOW, path) == "saved"
    assert limits.latest(path, NOW)["limit_5h"] == 41.0 and seen["t"] == "tok"
    assert claude_login.refresh_if_due(NOW + 10, path) == "fresh"  # not asked again so soon


def test_failures_report_status_without_the_token(monkeypatch, tmp_path):
    logins(monkeypatch, oauth("secret-token"))

    def refuse(token):
        raise urllib.error.HTTPError(claude_login.URL, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(claude_login, "fetch", refuse)
    result = claude_login.refresh_if_due(NOW, tmp_path / "l.json")
    assert result == "failed: HTTP 401" and "secret" not in result
    assert not (tmp_path / "l.json").exists()


def test_no_login_means_nothing_is_asked(monkeypatch, tmp_path):
    logins(monkeypatch)
    monkeypatch.setattr(claude_login, "fetch", lambda t: (_ for _ in ()).throw(AssertionError))
    assert claude_login.refresh_if_due(NOW, tmp_path / "l.json") == "no-login"


def test_usage_reply_without_windows_saves_nothing(tmp_path):
    assert not limits.record_usage_reply({"extra_usage": {}}, tmp_path / "l.json")
    assert json.dumps(limits.latest(tmp_path / "l.json")) == "{}"
