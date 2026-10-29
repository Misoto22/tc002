"""Install the Claude Code hooks that feed DONE / WAIT to the Claude screen.

Edits ~/.claude/settings.json in place: adds one command hook per event, leaves every
other hook untouched, and backs the file up before the first change.
"""

import json
import os
import shutil
from pathlib import Path

SETTINGS = Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).expanduser() / "settings.json"
EVENTS = {"Stop": "done", "Notification": "wait", "UserPromptSubmit": "clear"}
MARKER = " event "  # every tc002 hook command is `<exe> event <kind> ...`


def command(executable, kind):
    # Hooks must never slow or fail a session: no output, and always exit 0.
    return f"{executable} event {kind} >/dev/null 2>&1 || true"


def _is_ours(hook, executable):
    cmd = hook.get("command", "")
    return cmd.startswith(f"{executable}{MARKER}") or "/tc002 event " in cmd


def _load(path):
    return json.loads(path.read_text()) if path.exists() else {}


def _save(path, data):
    backup = path.with_name(path.name + ".bak-tc002")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def install(executable, path=SETTINGS):
    """Add (or refresh) the three hooks; returns the events changed."""
    data = _load(path)
    hooks = data.setdefault("hooks", {})
    changed = []
    for event, kind in EVENTS.items():
        entries = hooks.setdefault(event, [])
        wanted = command(executable, kind)
        present = [h for e in entries for h in e.get("hooks", []) if _is_ours(h, executable)]
        if [h.get("command") for h in present] == [wanted]:
            continue
        _strip(entries, executable)
        entries.append({"hooks": [{"type": "command", "command": wanted}]})
        changed.append(event)
    if changed:
        _save(path, data)
    return changed


def uninstall(executable, path=SETTINGS):
    data = _load(path)
    hooks = data.get("hooks", {})
    changed = []
    for event in EVENTS:
        entries = hooks.get(event, [])
        if _strip(entries, executable):
            changed.append(event)
        if not entries:
            hooks.pop(event, None)
    if changed:
        _save(path, data)
    return changed


def _strip(entries, executable):
    """Remove our hooks from a list of hook groups; drop groups left empty."""
    removed = False
    for entry in list(entries):
        kept = [h for h in entry.get("hooks", []) if not _is_ours(h, executable)]
        if len(kept) != len(entry.get("hooks", [])):
            removed = True
            if kept:
                entry["hooks"] = kept
            else:
                entries.remove(entry)
    return removed


def status(executable, path=SETTINGS):
    hooks = _load(path).get("hooks", {})
    return {
        event: any(
            _is_ours(h, executable) for e in hooks.get(event, []) for h in e.get("hooks", [])
        )
        for event in EVENTS
    }
