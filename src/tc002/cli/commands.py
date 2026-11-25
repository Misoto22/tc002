"""Command handlers. Each takes the parsed args plus a context, calls the application
layer (`tc002.app.App`) and prints its result; it returns an exit code."""

import json
import time
from dataclasses import dataclass

from ..app import App


@dataclass
class Context:
    app: App


def _say(ok, label, detail=""):
    mark = {True: "ok  ", False: "FAIL", None: "warn"}[ok]
    print(f"[{mark}] {label}{': ' + detail if detail else ''}")
    return ok is not False


# -- content ----------------------------------------------------------------------


def text(args, ctx):
    ctx.app.send_text(args.text, args.color, args.app, args.passes, args.show)
    return 0


def alert(args, ctx):
    ctx.app.send_alert(args.text, args.kind, args.color, args.app, args.seconds, args.keep)
    return 0


def watch(args, ctx):
    ctx.app.watch(once=args.once)
    return 0


# -- device -----------------------------------------------------------------------


def info(args, ctx):
    print(json.dumps(ctx.app.info(), indent=2, ensure_ascii=False))
    return 0


def apps(args, ctx):
    print("\n".join(ctx.app.custom_apps()) or "(none)")
    return 0


def rm(args, ctx):
    for app in ctx.app.remove_apps(args.apps):
        print(f"removed {app}")
    return 0


def layout(args, ctx):
    {"show": show_layout, "apply": apply_layout, "restore": restore_layout}[args.action](ctx)
    return 0


def show_layout(ctx):
    layout = ctx.app.layout()
    for category, saved in layout["categories"].items():
        on = [k for k, v in saved["enable"].items() if v]
        print(f"{category:9} on: {', '.join(on) or '-'}")
    print(f"carousel: {layout['carouselSpeed']}s (0 = off)")
    print(f"tc002.toml keeps: {', '.join(layout['keepBuiltins']) or '-'}")


def apply_layout(ctx):
    """Make the clock match tc002.toml (saving its original layout first)."""
    print("\n".join(ctx.app.apply()) or "the clock already matches tc002.toml")


def restore_layout(ctx):
    print(f"restored built-in apps and settings from {ctx.app.restore()}")


# -- host integration --------------------------------------------------------------


def service(args, ctx):
    if args.action == "install":
        print(f"installed {ctx.app.service_install()['plist']}")
    elif args.action == "uninstall":
        print(f"removed {ctx.app.service_uninstall()['plist']}")
    print(ctx.app.service_status())
    return 0


def hooks(args, ctx):
    if args.action == "install":
        _print_connected(ctx.app.connect_claude())
    elif args.action == "uninstall":
        _print_disconnected(ctx.app.disconnect_claude())
    state = ctx.app.claude_status()
    for event, present in state["hooks"].items():
        print(f"  {event:17} {'installed' if present else '-'}")
    print(f"  {'status line':17} {'wrapped' if state['statusline'] else '-'}")
    return 0


def _print_connected(done):
    print("hooks added: " + (", ".join(done["hooks"]) or "already installed"))
    wrapped = done["statusline"]
    print("status line: " + ("now saves plan limits" if wrapped else "already saves plan limits"))


def _print_disconnected(done):
    print("hooks removed: " + (", ".join(done["hooks"]) or "none were installed"))
    if done["statusline"]:
        print("status line: restored")


def install(args, ctx):
    done = ctx.app.install()
    _print_connected(done["claude"])
    layout = done["layout"]
    if layout["applied"]:
        print("\n".join(layout["changes"]) or "the clock already matches tc002.toml")
    elif not ctx.app.host:
        print("layout not applied: no clock configured; run `tc002 setup` first")
    else:
        error = layout["error"]
        print(f"layout not applied, clock unreachable ({error}); run `tc002 layout apply` later")
    print(f"service: {done['service']}")
    return 0


def uninstall(args, ctx):
    done = ctx.app.uninstall()
    print("service removed")
    _print_disconnected(done["claude"])
    if done.get("error"):
        print(f"built-in apps not restored: {done['error']}")
    elif done["restored"]:
        print(f"restored built-in apps and settings from {done['restored']}")
    return 0


def ui(args, ctx):
    import webbrowser

    from ..web import server

    def ready(url):
        print(f"tc002 UI at {url}  (Ctrl-C to stop)")
        if not args.no_open:
            webbrowser.open(url)

    server.serve(App.local(), port=args.port, ready=ready)
    return 0


def mcp(args, ctx):
    from ..mcp import server

    server.serve(ctx.app)
    return 0


def doctor(args, ctx):
    healthy = True
    for check in ctx.app.checks():
        healthy &= _say(check["ok"], check["name"], check["detail"])
    return 0 if healthy else 1


def focus(args, ctx):
    """Start or stop the focus timer; the focus screen shows it (enable it to see it)."""
    if args.action == "stop":
        ctx.app.focus_stop()
        print("focus timer stopped")
        return 0
    done = ctx.app.focus_start(args.minutes)
    print(f"focus: {done['minutes']} min, then a {done['break']} min break")
    if not done["screenEnabled"]:
        print("note: the focus screen is not enabled; turn it on in `tc002 ui` → Rotation")
    return 0


def display(args, ctx):
    """Screen off now / back on, or show whether it is dark and why."""

    def at(epoch):
        return time.strftime("%H:%M", time.localtime(epoch))

    if args.action == "off":
        st = ctx.app.screen_off(until_morning=args.until_morning)
        until = st["until"] if args.until_morning else None
        print(f"screen off until {at(until) if until else 'you turn it on'}")
    elif args.action == "on":
        st = ctx.app.screen_on()
    else:
        st = ctx.app.night_status()
    sched = st["schedule"]
    why = {"off": "screen off", "on": "kept on", "schedule": "night schedule"}.get(st["why"])
    line = "dark" if st["dark"] else "on"
    if why:
        line += f" ({why})"
    if st["until"]:
        line += f" until {at(st['until'])}"
    plan = f"{sched['start']}-{sched['end']}" if sched["enable"] else "off"
    print(f"screen: {line}")
    print(f"night schedule: {plan} (now {st['time']})")
    return 0
