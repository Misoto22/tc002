"""Command handlers. Each takes the parsed args plus a context and returns an exit code."""

import json
import time
from dataclasses import dataclass

from .. import builtins, config, sync
from ..device import MIN_FIRMWARE, Device, DeviceError, firmware
from ..integrations import claude_hooks, executable, launchd, statusline
from ..runtime import sessions, watcher
from ..runtime.output import Output
from ..screens import message


@dataclass
class Context:
    settings: config.Settings
    device: Device | None  # None in --preview mode
    out: Output


def _say(ok, label, detail=""):
    mark = {True: "ok  ", False: "FAIL", None: "warn"}[ok]
    print(f"[{mark}] {label}{': ' + detail if detail else ''}")
    return ok is not False


# -- content ----------------------------------------------------------------------


def text(args, ctx):
    segments = message.text_animation(args.text, args.color)
    if len(segments) == 1:
        ctx.out.show(args.app, segments[0])
    else:  # long text: segments back to back, then leave the clock clean
        for _ in range(max(1, args.passes)):
            for seg in segments:
                ctx.out.show(args.app, seg)
                if ctx.device is None:
                    break
                time.sleep(seg.duration_s())
        if ctx.device is not None:
            ctx.out.remove(args.app)
            return 0
    if args.show and ctx.device is not None:
        ctx.device.switch_custom(args.app)
    return 0


def alert(args, ctx):
    ctx.out.show(args.app, message.alert_animation(args.text, args.kind, args.color))
    if ctx.device is None:
        return 0
    ctx.device.switch_custom(args.app)
    if not args.keep:
        time.sleep(args.seconds)
        ctx.out.remove(args.app)
    return 0


def watch(args, ctx):
    watcher.watch(ctx.device, ctx.settings, ctx.out.preview_dir, once=args.once)
    return 0


# -- device -----------------------------------------------------------------------


def info(args, ctx):
    print(json.dumps(ctx.device.info(), indent=2, ensure_ascii=False))
    return 0


def apps(args, ctx):
    print("\n".join(ctx.device.apps()) or "(none)")
    return 0


def rm(args, ctx):
    for app in args.apps or ctx.device.apps():
        ctx.device.remove(app)
        print(f"removed {app}")
    return 0


def layout(args, ctx):
    {"show": show_layout, "apply": apply_layout, "restore": restore_layout}[args.action](ctx)
    return 0


def show_layout(ctx):
    dev, settings = ctx.device, ctx.settings
    snap = builtins.snapshot(dev)
    for category, saved in snap.items():
        on = [k for k, v in saved["enable"].items() if v]
        print(f"{category:9} on: {', '.join(on) or '-'}")
    print(f"carousel: {dev.config().get('carouselSpeed')}s (0 = off)")
    print(f"tc002.toml keeps: {', '.join(settings.keep_builtins) or '-'}")


def apply_layout(ctx):
    """Make the clock match tc002.toml (saving its original layout first)."""
    changes = sync.apply(ctx.device, ctx.settings, config.STATE_DIR)
    print("\n".join(changes) or "the clock already matches tc002.toml")


def restore_layout(ctx):
    path = sync.restore(ctx.device, config.STATE_DIR)
    print(f"restored built-in apps and settings from {path}")


# -- host integration --------------------------------------------------------------


def service(args, ctx):
    if args.action == "install":
        launchd.install(executable())
        print(f"installed {launchd.PLIST}")
    elif args.action == "uninstall":
        launchd.uninstall()
        print(f"removed {launchd.PLIST}")
    print(launchd.status())
    return 0


def hooks(args, ctx):
    exe = executable()
    if args.action == "install":
        _connect_claude(exe)
    elif args.action == "uninstall":
        _disconnect_claude(exe)
    for event, present in claude_hooks.status(exe).items():
        print(f"  {event:17} {'installed' if present else '-'}")
    print(f"  {'status line':17} {'wrapped' if statusline.status(exe) else '-'}")
    return 0


def _connect_claude(exe):
    print("hooks added: " + (", ".join(claude_hooks.install(exe)) or "already installed"))
    wrapped = statusline.install(exe)
    print("status line: " + ("now saves plan limits" if wrapped else "already saves plan limits"))


def _disconnect_claude(exe):
    print("hooks removed: " + (", ".join(claude_hooks.uninstall(exe)) or "none were installed"))
    if statusline.uninstall(exe):
        print("status line: restored")


def install(args, ctx):
    exe = executable()
    _connect_claude(exe)
    if ctx.device is None:
        print("layout not applied: no clock configured; run `tc002 setup` first")
    else:
        try:
            apply_layout(ctx)
        except DeviceError as exc:
            print(f"layout not applied, clock unreachable ({exc}); run `tc002 layout apply` later")
    launchd.install(exe)
    print(f"service: {launchd.status()}")
    return 0


def uninstall(args, ctx):
    launchd.uninstall()
    print("service removed")
    _disconnect_claude(executable())
    if ctx.device is None:
        return 0
    try:
        restore_layout(ctx)
    except (DeviceError, FileNotFoundError) as exc:
        print(f"built-in apps not restored: {exc}")
    return 0


def ui(args, ctx):
    import webbrowser

    from ..web import server

    def ready(url):
        print(f"tc002 UI at {url}  (Ctrl-C to stop)")
        if not args.no_open:
            webbrowser.open(url)

    server.serve(config.host(), config.path(), port=args.port, ready=ready)
    return 0


def doctor(args, ctx):
    healthy = _say(True, "config", ctx.settings.source)
    if ctx.device is None:
        healthy &= _say(False, "clock", "no host: run `tc002 setup --host <IP>`")
    else:
        try:
            base = ctx.device.info()["base"]
            fw = firmware(base.get("appVer"))
            _say(True, "clock", f"{ctx.device.base} firmware {base.get('appVer')}")
            healthy &= _say(
                fw >= MIN_FIRMWARE or None,
                "firmware",
                "screen switching supported" if fw >= MIN_FIRMWARE else "update for switching",
            )
            _say(True, "custom apps", ", ".join(ctx.device.apps()) or "(none)")
        except DeviceError as exc:
            healthy &= _say(False, "clock", str(exc))
    status = launchd.status()
    healthy &= _say(status.startswith("state: running") or None, "service", status.splitlines()[0])
    try:
        hook_state = claude_hooks.status(executable())
        healthy &= _say(all(hook_state.values()) or None, "hooks", json.dumps(hook_state))
    except RuntimeError as exc:
        healthy &= _say(None, "hooks", str(exc))
    healthy &= _say(statusline.status(executable()) or None, "status line", "saves plan limits")
    known = sessions.load()
    latest = f"{known[0].project} {known[0].state} {time.time() - known[0].since:.0f}s ago"
    _say(True, "sessions", f"{len(known)} known, latest: {latest}" if known else "none yet")
    return 0 if healthy else 1


def focus(args, ctx):
    """Start or stop the focus timer; the focus screen shows it (enable it to see it)."""
    from ..runtime import focus as timer
    from ..screens import build

    if args.action == "stop":
        timer.stop()
        print("focus timer stopped")
        return 0
    screen = build("focus", ctx.settings)
    minutes = args.minutes or screen.minutes
    timer.start(minutes, screen.break_minutes)
    print(f"focus: {minutes} min, then a {screen.break_minutes} min break")
    if "focus" not in ctx.settings.screens:
        print("note: the focus screen is not enabled; turn it on in `tc002 ui` → Rotation")
    return 0
