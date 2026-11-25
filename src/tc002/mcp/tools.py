"""The MCP tools: each one is an `App` method with a JSON Schema for its arguments.

Read-only tools never change the clock, tc002.toml or this Mac. The others say in their
description exactly what they change and whether it lasts; their annotations
(`readOnlyHint`, `destructiveHint`, `idempotentHint`) let a client ask before running
the risky ones.
"""

from dataclasses import dataclass, field

from .. import builtins, config, device_settings
from ..screens import SCREENS, message


@dataclass(frozen=True)
class Tool:
    name: str
    title: str
    description: str
    run: object  # (app, arguments) -> result
    properties: dict = field(default_factory=dict)
    required: tuple = ()
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False

    @property
    def input_schema(self):
        return {
            "type": "object",
            "properties": self.properties,
            "required": list(self.required),
            "additionalProperties": False,
        }

    def describe(self):
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {
                "title": self.title,
                "readOnlyHint": self.read_only,
                "destructiveHint": self.destructive,
                "idempotentHint": self.idempotent,
                "openWorldHint": False,  # one clock on the LAN and files on this Mac
            },
        }


def _display_schema():
    """`[display]` settings as JSON Schema, from the same table that validates tc002.toml."""
    props = {}
    for key, (kind, label, spec) in device_settings.DISPLAY.items():
        if kind == "bool":
            props[key] = {"type": "boolean", "description": label}
        elif kind == "int":
            props[key] = {
                "type": "integer",
                "minimum": spec[0],
                "maximum": spec[1],
                "description": label,
            }
        else:
            props[key] = {"enum": list(spec), "description": label}
    if "auto" in device_settings.TIMEZONES:
        props["timezone"]["description"] = (
            'Time zone: "auto" follows this Mac (summer time included), else a fixed UTC offset.'
        )
    lo, hi = device_settings.BRIGHTNESS_RANGE
    level = {"type": "integer", "minimum": lo, "maximum": hi}
    props["brightness"] = {
        "type": "object",
        "description": (
            "Brightness: `level` picks which preset is active; `low`/`mid`/`high` are the "
            f"presets in % ({lo}-{hi}, low < mid < high). Give only what changes."
        ),
        "properties": {
            "level": {"enum": device_settings.BRIGHTNESS_LEVELS},
            "low": level,
            "mid": level,
            "high": level,
        },
        "additionalProperties": False,
    }
    return props


SCREEN_NAMES = list(SCREENS)
BUILTIN_NAMES = list(builtins.CATALOGUE)

READ_ONLY = [
    Tool(
        "get_status",
        "Clock status",
        "Is the clock reachable (host, firmware, custom apps on it), is the background "
        "service running, is the screen dark (night mode), is a focus timer or a live "
        "preview running. Start here. Changes nothing.",
        lambda app, a: app.status(),
        read_only=True,
        idempotent=True,
    ),
    Tool(
        "list_screens",
        "List screens",
        "Every live screen tc002 can draw and every built-in clock app, with whether each "
        "is enabled and how many seconds it gets in the rotation. Use these names with "
        "show_screen. Changes nothing.",
        lambda app, a: app.screens(),
        read_only=True,
        idempotent=True,
    ),
    Tool(
        "now_showing",
        "What drives the screen",
        "What tc002 is putting on the screen now: night (dark), a live preview, or the "
        "rotation (with its slots). The clock does not report its current app, so this is "
        "tc002's side of it. Changes nothing.",
        lambda app, a: app.now_showing(),
        read_only=True,
        idempotent=True,
    ),
    Tool(
        "get_config",
        "Read tc002.toml",
        "The saved tc002.toml as JSON (screens, rotation, display, apps, night, ...) and "
        "its path. Edit this document and pass it to save_config. Changes nothing.",
        lambda app, a: app.config_data(),
        read_only=True,
        idempotent=True,
    ),
    Tool(
        "get_clock_settings",
        "Read the clock's settings",
        "The clock's live settings that tc002 manages (brightness, volume, built-in apps "
        "on/off, their options) and `drift`: where the clock differs from tc002.toml. "
        "Credentials are reported only as present. Changes nothing.",
        lambda app, a: app.clock_state(),
        read_only=True,
        idempotent=True,
    ),
    Tool(
        "run_checks",
        "Health checks",
        "`tc002 doctor`: config, clock, firmware, service, Claude Code hooks and status "
        "line, sessions. Each check is ok (true), failed (false) or a warning (null). "
        "Changes nothing.",
        lambda app, a: {"checks": app.checks()},
        read_only=True,
        idempotent=True,
    ),
]

ACTIONS = [
    Tool(
        "show_screen",
        "Switch the screen",
        "Put one live screen or one built-in app on the clock now. Temporary: the "
        "rotation moves on at its next slot. Give exactly one of `screen` or `builtin` "
        "(names from list_screens). Does not change tc002.toml.",
        lambda app, a: app.show(a.get("screen"), a.get("builtin")),
        {
            "screen": {"enum": SCREEN_NAMES, "description": "A tc002 live screen."},
            "builtin": {"enum": BUILTIN_NAMES, "description": "A built-in clock app."},
        },
        idempotent=True,
    ),
    Tool(
        "send_message",
        "Show a message",
        "Play a short text or an alert (icon and chasing lights) on the clock, then go "
        "back to the rotation by itself (about 10 s; long text scrolls). Returns at once "
        f"with how long it plays. Text up to {message.MAX_CHARS} characters, alerts up to "
        f"{message.ALERT_MAX_CHARS}. Nothing is saved.",
        lambda app, a: app.play_message(
            a["text"], a.get("type", "text"), a.get("kind", "done"), a.get("color")
        ),
        {
            "text": {"type": "string", "minLength": 1, "maxLength": message.MAX_CHARS},
            "type": {"enum": ["text", "alert"], "default": "text"},
            "kind": {
                "enum": list(message.ICONS),
                "default": "done",
                "description": "Alert icon and colour (alerts only).",
            },
            "color": {
                "type": "string",
                "description": f"{', '.join(message.COLORS)} or #RRGGBB.",
            },
        },
        required=("text",),
    ),
    Tool(
        "screen_off",
        "Screen off",
        "Turn the screen fully dark now; the service pauses until screen_on (or, with "
        "`until_morning`, until the night schedule ends, else 07:00). Lasts across "
        "restarts; does not change tc002.toml.",
        lambda app, a: app.screen_off(bool(a.get("until_morning"))),
        {"until_morning": {"type": "boolean", "default": False}},
        idempotent=True,
    ),
    Tool(
        "screen_on",
        "Screen on",
        "Light the screen again and resume the rotation. Inside the night schedule it "
        "stays lit until the schedule ends tonight. Does not change tc002.toml.",
        lambda app, a: app.screen_on(),
        idempotent=True,
    ),
    Tool(
        "focus_start",
        "Start focus timer",
        "Start a focus timer (then a break) that the `focus` screen shows. Replaces a "
        "running one. The focus screen must be enabled to be seen (`screenEnabled`).",
        lambda app, a: app.focus_start(a.get("minutes")),
        {"minutes": {"type": "integer", "minimum": 1, "maximum": 180}},
    ),
    Tool(
        "focus_stop",
        "Stop focus timer",
        "Stop the focus timer, if one runs; the focus screen goes back to idle.",
        lambda app, a: app.focus_stop(),
        idempotent=True,
    ),
    Tool(
        "set_display",
        "Change display settings",
        "Change the clock's display settings (brightness, volume, time zone, ...): "
        "saved into tc002.toml AND applied to the clock at once. Only the keys given "
        "change. Lasting: overwrites the previous values in tc002.toml.",
        lambda app, a: app.set_display(a["display"]),
        {
            "display": {
                "type": "object",
                "properties": _display_schema(),
                "additionalProperties": False,
                "minProperties": 1,
            }
        },
        required=("display",),
        destructive=True,
        idempotent=True,
    ),
    Tool(
        "save_config",
        "Save tc002.toml",
        "Replace tc002.toml with `data` (the whole document, as get_config returns it), "
        "validate it first (nothing is written if invalid), push it to the clock and "
        "restart the background service. Lasting and overwrites the file: read with "
        "get_config, change only what was asked, send it all back with `expected_version` "
        "so a file changed meanwhile is not overwritten.",
        lambda app, a: app.save_config(a["data"], expected=a.get("expected_version")),
        {
            "data": {
                "type": "object",
                "description": "Tables: " + ", ".join(sorted(config.SECTION_KEYS)) + ".",
            },
            "expected_version": {
                "type": "string",
                "description": "`version` from get_config; refused if the file changed since.",
            },
        },
        required=("data",),
        destructive=True,
        idempotent=True,
    ),
    Tool(
        "apply_layout",
        "Apply tc002.toml to the clock",
        "Make the clock match tc002.toml now: built-in apps on/off, display and app "
        "settings, carousel off. Saves the clock's original layout first (once) so "
        "restore_layout can undo it. Overwrites settings changed on the clock itself.",
        lambda app, a: {"changes": app.apply()},
        destructive=True,
        idempotent=True,
    ),
    Tool(
        "restore_layout",
        "Restore the original layout",
        "Put the clock's built-in apps and settings back to how they were before tc002 "
        "first changed them. The running service will re-apply tc002.toml when it "
        "restarts; use this when the user wants tc002's layout gone.",
        lambda app, a: {"restoredFrom": app.restore()},
        destructive=True,
        idempotent=True,
    ),
    Tool(
        "restart_service",
        "Restart the service",
        "Restart the launchd background service so it re-reads tc002.toml (no-op when "
        "not installed). The screens blink back within seconds.",
        lambda app, a: app.service_restart(),
        idempotent=True,
    ),
]

TOOLS = {t.name: t for t in READ_ONLY + ACTIONS}
