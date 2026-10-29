"""Argument parser: every command, its options and its help text."""

import argparse
from importlib.metadata import version

from ..runtime import events
from ..screens import message

EPILOG = """\
first run:
  uv tool install .                              # from the clone
  tc002 setup --host 192.168.1.50 --config ./tc002.toml
  tc002 install                                  # layout + background service + hooks

day to day:
  tc002 text "BUILD OK" --color green
  tc002 alert "DEPLOYED" --kind done
  tc002 doctor
"""


def build():
    p = argparse.ArgumentParser(
        prog="tc002",
        description="Animated screens and control for the Ulanzi TC002 pixel clock.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {version('tc002')}")
    p.add_argument("--host", help="clock IP (default: $TC002_HOST, then `tc002 setup`)")
    p.add_argument("--config", help="tc002.toml to use (default: $TC002_CONFIG, then setup)")
    p.add_argument(
        "--preview",
        metavar="DIR",
        help="write LED mock-up GIFs to DIR instead of pushing to the clock",
    )
    sub = p.add_subparsers(dest="cmd", required=True, metavar="command")

    s = sub.add_parser("setup", help="remember the clock's IP and your tc002.toml")
    s.add_argument("--host", dest="setup_host", required=True)
    s.add_argument("--config", dest="setup_config", help="path to your tc002.toml")

    sub.add_parser("install", help="apply the layout, start the service, add Claude hooks")
    sub.add_parser("uninstall", help="stop the service, remove hooks, restore built-in apps")
    sub.add_parser("doctor", help="check config, clock, firmware, service and hooks")
    ui = sub.add_parser("ui", help="open the settings UI in your browser (local only)")
    ui.add_argument("--port", type=int, default=8742, help="local port (default 8742)")
    ui.add_argument("--no-open", action="store_true", help="do not open a browser")

    sub.add_parser("info", help="clock firmware, Wi-Fi and global settings")
    sub.add_parser("apps", help="list custom apps on the clock")
    rm = sub.add_parser("rm", help="remove custom apps (all when none named)")
    rm.add_argument("apps", nargs="*")

    t = sub.add_parser("text", help="show text: short text shimmers, long text scrolls")
    t.add_argument("text")
    t.add_argument("--color", default="white", help=f"{', '.join(message.COLORS)} or #RRGGBB")
    t.add_argument("--app", default="msg", help="custom app name (default: msg)")
    t.add_argument("--passes", type=int, default=2, help="marquee passes for long text")
    t.add_argument("--show", action="store_true", help="switch the clock to it")

    a = sub.add_parser("alert", help="alert with chasing border lights")
    a.add_argument("text")
    a.add_argument("--kind", choices=list(message.ICONS), default="done")
    a.add_argument("--color", help="override the kind's colour")
    a.add_argument("--seconds", type=float, default=10, help="how long before removal")
    a.add_argument("--app", default="alert")
    a.add_argument("--keep", action="store_true", help="leave it on the clock")

    e = sub.add_parser("event", help="record a Claude Code hook event (used by the hooks)")
    e.add_argument("kind", choices=events.KINDS)

    w = sub.add_parser("watch", help="run screens + rotation in the foreground")
    w.add_argument("--once", action="store_true", help="push one animation per screen, exit")

    lay = sub.add_parser("layout", help="which built-in apps stay on, and the carousel")
    lay.add_argument("action", choices=["show", "apply", "restore"])

    svc = sub.add_parser("service", help="the launchd background service")
    svc.add_argument("action", choices=["install", "uninstall", "status"])

    hk = sub.add_parser("hooks", help="the Claude Code hooks in ~/.claude/settings.json")
    hk.add_argument("action", choices=["install", "uninstall", "status"])
    return p
