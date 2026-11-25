"""`tc002` entry point: parse, build the App, dispatch, map errors to exit codes."""

import sys

from ..app import App, AppError
from . import commands, parser

# Commands that never talk to the clock.
LOCAL_ONLY = {"setup", "service", "hooks", "ui", "focus", "mcp"}
PREVIEWABLE = {"text", "alert", "watch"}


def _from_claude(args):
    """Commands Claude Code runs (hooks, status line): never block or fail it over tc002."""
    app = App()
    if args.cmd == "statusline":
        sys.stdout.buffer.write(app.statusline(sys.stdin.buffer.read()))
        return 0
    try:
        if args.cmd == "hook":
            app.record_hook(sys.stdin.read())
        else:
            app.record_event(args.kind)
    except (OSError, ValueError) as exc:
        print(f"tc002: could not record {args.cmd}: {exc}", file=sys.stderr)
    return 0


def main(argv=None):
    args = parser.build().parse_args(argv)

    if args.cmd in ("hook", "statusline", "event"):
        return _from_claude(args)
    try:
        if args.cmd == "setup":
            done = App().setup_local(args.setup_host, args.setup_config)
            print(f"saved to {done['file']}: {done['saved']}")
            return 0
        if args.preview and args.cmd not in PREVIEWABLE:
            sys.exit(f"tc002: --preview only applies to text, alert and watch, not {args.cmd}")
        app = App.local(args.host, args.config, preview_dir=args.preview)
        app.settings()  # fail early on a broken tc002.toml
        needs_clock = args.cmd not in LOCAL_ONLY and args.cmd != "doctor"
        if args.preview is None and app.host is None and needs_clock:
            sys.exit("tc002: no clock configured; run `tc002 setup --host <IP>` or set TC002_HOST")
        return getattr(commands, args.cmd)(args, commands.Context(app))
    except AppError as exc:
        sys.exit(f"tc002: {exc.detail}")
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        sys.exit(f"tc002: {exc}")
