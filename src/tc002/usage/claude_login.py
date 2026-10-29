"""Claude plan limits from Anthropic's usage endpoint, asked with Claude Code's own login.

The desktop app never runs a status line, so `tc002 statusline` alone cannot see the
limits there. This asks the endpoint Claude Code itself uses (/api/oauth/usage) at most
every REFRESH seconds and saves the percentages through limits.py.

The login token is read from the macOS Keychain item Claude Code keeps ("Claude
Code-credentials"; ~/.claude/.credentials.json elsewhere) on each call and held only in
memory: never written, logged or put in an error message. It is never refreshed here:
refreshing rotates the token and would sign Claude Code out. An expired token means
waiting until Claude Code refreshes it.
"""

import json
import subprocess
import time
import urllib.error
import urllib.request

from .. import paths
from . import limits

URL = "https://api.anthropic.com/api/oauth/usage"
KEYCHAIN_SERVICE = "Claude Code-credentials"
CREDENTIALS_FILE = paths.CLAUDE_DIR / ".credentials.json"
REFRESH = 300  # seconds between asks, shared by every tc002 process through the limits file
TIMEOUT = 10


def _logins():
    """Claude Code's stored login documents, Keychain first, then the credentials file."""
    try:
        found = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if found.returncode == 0 and found.stdout.strip():
            yield json.loads(found.stdout)
    except OSError, subprocess.SubprocessError, ValueError:
        pass  # no Keychain (Linux) or an unreadable item: the file is next
    try:
        yield json.loads(CREDENTIALS_FILE.read_text())
    except OSError, ValueError:
        return


def access_token(now=None):
    """The first stored OAuth access token that is present and not expired, or None."""
    now = time.time() if now is None else now
    for login in _logins():
        token = _usable((login or {}).get("claudeAiOauth") or {}, now)
        if token:
            return token
    return None


def _usable(login, now):
    token, expires = login.get("accessToken"), login.get("expiresAt")
    if not isinstance(token, str) or not token:
        return None
    # 0 means no expiry recorded; a real one may be in seconds or milliseconds. When in
    # doubt, ask anyway: the server's 401 is the authority.
    if isinstance(expires, int | float) and expires > 1e9:
        expires_at = expires / 1000 if expires > 1e11 else expires
        if expires_at <= now + 30:
            return None
    return token


def fetch(token):
    """The usage reply as a dict. Errors carry the status, never the request headers."""
    req = urllib.request.Request(
        URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "tc002",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def refresh_if_due(now=None, path=None):
    """Ask for fresh limits when the saved ones are older than REFRESH.

    Returns "fresh", "saved", "no-login" or "failed: <reason>"; never raises, because a
    screen or a page must keep working when the network or the login does not.
    """
    if limits.age(path, now) < REFRESH:
        return "fresh"
    token = access_token(now)
    if token is None:
        return "no-login"
    try:
        reply = fetch(token)
    except urllib.error.HTTPError as exc:
        return f"failed: HTTP {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return f"failed: {type(exc).__name__}"
    return "saved" if limits.record_usage_reply(reply, path, now) else "failed: no limits in reply"
