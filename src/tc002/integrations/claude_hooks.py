"""Install the Claude Code hooks that tell tc002 what each session is doing.

Edits ~/.claude/settings.json in place: adds one `tc002 hook` command per event (it
reads the event from stdin, see runtime/sessions.py), leaves every other hook
untouched, and backs the file up before the first change. Hooks from older tc002
versions (`tc002 event <kind>`) are recognised and replaced.
"""

import json
import shutil

from .. import paths

SETTINGS = paths.CLAUDE_DIR / "settings.json"
EVENTS = ("SessionStart", "UserPromptSubmit", "Notification", "Stop", "SessionEnd")
MARKERS = (" hook", " event ")  # `<exe> hook`, and `<exe> event <kind>` from older versions


def command(executable):
    # Hooks must never slow or fail a session: no output, and always exit 0.
    return f"{executable} hook >/dev/null 2>&1 || true"


def _is_ours(hook, executable):
    cmd = hook.get("command", "")
    return any(cmd.startswith(executable + m) or f"/tc002{m}" in cmd for m in MARKERS)


def _load(path):
    return json.loads(path.read_text()) if path.exists() else {}


def _save(path, data):
    backup = path.with_name(path.name + ".bak-tc002")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def install(executable, path=SETTINGS):
    """Add (or refresh) the hooks; returns the events changed."""
    data = _load(path)
    hooks = data.setdefault("hooks", {})
    changed = []
    for event in EVENTS:
        entries = hooks.setdefault(event, [])
        wanted = command(executable)
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
