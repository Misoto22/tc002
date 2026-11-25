"""The application layer: every use case tc002 offers, in one place.

The CLI (`cli/`), the web API (`web/`) and the MCP server (`mcp/`) are thin front ends
over `App`: they turn their input into a method call and its result (a plain dict, list,
string or bytes) into their output. They import nothing else from tc002 except
`app.catalog` (names and allowed values) and `app.errors`; tests/test_architecture.py
enforces that.

`App` is put together from one class per topic, each in its own module:

| Module | Use cases |
|---|---|
| `reads.py` | status, overview, screens, now showing, tc002.toml, clock state, doctor checks |
| `screen.py` | switch, messages, screen off/on, focus timer, games, the service in the foreground |
| `settings.py` | save tc002.toml (validate, write, apply, restart), display, live drafts |
| `host.py` | the launchd service, Claude Code hooks and status line, secrets, log, Finder |
| `setup.py` | remember a clock, discovery, first tc002.toml, Wi-Fi for a new clock |
| `content.py` | LED previews, trying a screen, the pickers' searches |

`base.py` holds what they share (which clock, which tc002.toml, the clock client) and
`guarded`, which turns every lower-level failure into one of `app.errors`.
"""

from .base import Base, guarded
from .content import Content
from .errors import (
    AppError,
    ClockUnreachable,
    CommandFailed,
    Conflict,
    InvalidRequest,
    InvalidSettings,
    NotConfigured,
    NotFound,
    ServiceUnavailable,
)
from .host import Host
from .reads import Reads
from .screen import OnScreen
from .settings import Configure
from .setup import Setup

__all__ = [
    "App",
    "AppError",
    "ClockUnreachable",
    "CommandFailed",
    "Conflict",
    "InvalidRequest",
    "InvalidSettings",
    "NotConfigured",
    "NotFound",
    "ServiceUnavailable",
]


@guarded
class App(Reads, OnScreen, Configure, Host, Setup, Content, Base):
    """One clock and one tc002.toml, and everything tc002 can do with them."""
