"""`tc002` entry point: parse, build the context, dispatch, map errors to exit codes."""

import json
import subprocess
import sys
from pathlib import Path

from .. import config
from ..device import Device, DeviceError
from ..runtime import sessions
from ..runtime.output import Output
from . import commands, parser

# Commands that never talk to the clock.
LOCAL_ONLY = {"setup", "service", "hooks", "ui", "focus"}


def _from_claude(args):
    """Commands Claude Code runs (hooks, status line): never block or fail it over tc002."""
    if args.cmd == "statusline":
        from ..integrations import statusline

        sys.stdout.buffer.write(statusline.run(sys.stdin.buffer.read()))
        return 0
    try:
        if args.cmd == "hook":
            sessions.record_hook(json.loads(sys.stdin.read() or "{}"))
        else:
            sessions.record_manual(args.kind)
    except (OSError, ValueError) as exc:
        print(f"tc002: could not record {args.cmd}: {exc}", file=sys.stderr)
    return 0


def main(argv=None):
    args = parser.build().parse_args(argv)

    if args.cmd in ("hook", "statusline", "event"):
        return _from_claude(args)

    if args.cmd == "setup":
        saved = config.save_local(
            host=args.setup_host,
            config=str(Path(args.setup_config).expanduser().resolve())
            if args.setup_config
            else None,
        )
        print(f"saved to {config.LOCAL_FILE}: {saved}")
        config.load()  # validate the chosen tc002.toml now rather than in the service
        return 0

    try:
        settings = config.load(args.config)
    except config.ConfigError as exc:
        sys.exit(f"tc002: {exc}")

    host = config.host(args.host)
    needs_clock = args.cmd not in LOCAL_ONLY and args.cmd != "doctor"
    if args.preview is None and host is None and needs_clock:
        sys.exit("tc002: no clock configured; run `tc002 setup --host <IP>` or set TC002_HOST")
    device = None if (args.preview or host is None) else Device(host)
    ctx = commands.Context(settings, device, Output(device, args.preview))

    if args.preview and args.cmd not in {"text", "alert", "watch"}:
        sys.exit(f"tc002: --preview only applies to text, alert and watch, not {args.cmd}")
    try:
        return getattr(commands, args.cmd)(args, ctx)
    except DeviceError as exc:
        sys.exit(f"tc002: {exc}")
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        sys.exit(f"tc002: {exc}")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"tc002: {(exc.stderr or str(exc)).strip()}")
