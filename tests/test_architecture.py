"""The architecture, as a contract the code is checked against (not a description of it).

Every module under src/tc002 belongs to exactly one unit in LAYERS, listed top to
bottom. A unit may import only what its `may_import` names (itself always), so:

- the three front ends (cli, web, mcp) reach the rest of tc002 only through `app`;
- below `app`, imports only point down, never sideways between siblings or up;
- nothing imports a third-party package (tc002 has no runtime dependencies);
- front ends do no I/O of their own beyond their transport (no subprocess, sockets
  or outgoing HTTP: that belongs to the units below).

docs/architecture.md shows the same table, generated from LAYERS (`render()`), and a
test keeps the two identical. To change the architecture, change LAYERS here, run
`uv run python tests/test_architecture.py` to print the new table, and paste it.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "tc002"
DOC = ROOT / "docs" / "architecture.md"

# unit -> (what it owns, what it may import). Order: top layer first.
LAYERS = {
    "cli": (
        "`tc002` commands: parse, call App, print; starts the web and MCP servers",
        ["app", "web.server", "mcp.server"],
    ),
    "web": ("`tc002 ui`: HTTP transport, request shapes, static front end", ["app"]),
    "mcp": ("`tc002 mcp`: JSON-RPC over stdio, tool schemas", ["app"]),
    "app": (
        "Every use case, as App methods; typed errors; the catalogue front ends show",
        [
            "config",
            "runtime",
            "screens",
            "games",
            "lookup",
            "host",
            "clock",
            "state",
            "usage",
            "render",
            "paths",
            "net",
        ],
    ),
    "config": (
        "tc002.toml: parse, validate, write; presets",
        ["runtime", "screens", "host", "clock", "render", "paths"],
    ),
    "runtime": (
        "Loops that drive the clock: service, rotation, output, night, game session",
        ["screens", "games", "clock", "state", "render", "paths"],
    ),
    "screens": (
        "Live screens: sample() -> state, render(state) -> Animation",
        ["host", "clock", "state", "usage", "render", "net", "paths"],
    ),
    "games": ("Game rules and drawing, no I/O", ["render"]),
    "lookup": ("Searches for the UI's pickers: cities, stock symbols", ["net"]),
    "host": (
        "This Mac: launchd, Claude Code hooks and status line, Keychain, Finder",
        ["usage", "paths"],
    ),
    "clock": ("The TC002: HTTP client, built-in apps, settings rules, sync, Wi-Fi, discovery", []),
    "state": ("Small state files shared by service, UI and hooks", ["paths"]),
    "usage": ("Claude Code and Codex usage read from local files", ["paths"]),
    "render": ("Pixels only: canvas, fonts, palette, GIF", []),
    "paths": ("Where tc002 keeps files", []),
    "net": ("Outgoing HTTP for screens and lookups", []),
}
ENTRY = {"tc002", "tc002.__main__"}  # the package marker and `python -m tc002`
FRONT_ENDS = ("cli", "web", "mcp")
FRONT_END_FORBIDDEN = {"subprocess", "socket", "urllib.request", "http.client"}


def modules():
    """{dotted name: path} for every module under src/tc002."""
    out = {}
    for path in SRC.rglob("*.py"):
        parts = path.relative_to(SRC.parent).with_suffix("").parts
        name = ".".join(parts).removesuffix(".__init__")
        out[name] = path
    return out


_MODULES = modules()


def unit_of(name):
    rest = name.removeprefix("tc002.")
    for unit in sorted(LAYERS, key=len, reverse=True):
        if rest == unit or rest.startswith(unit + "."):
            return unit
    return None


def imports(name, path):
    """(target, line) for every import in the module, lazy ones in functions included.
    `from pkg import mod` names `pkg.mod`; `from mod import func` names `mod`."""
    known = _MODULES
    package = name if path.name == "__init__.py" else name.rsplit(".", 1)[0]
    found = []
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if isinstance(node, ast.Import):
            found += [(alias.name, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module
            for alias in node.names:
                sub = f"{target}.{alias.name}"
                found.append((sub if sub in known else target, node.lineno))
    return found


def _allowed(unit, target):
    if unit_of(target) == unit:
        return True
    rest = target.removeprefix("tc002.")
    return any(rest == a or rest.startswith(a + ".") for a in LAYERS[unit][1])


def _resolve(target, known):
    """The tc002 module an import names (`from .x import y` may name a function)."""
    while target not in known and "." in target:
        target = target.rsplit(".", 1)[0]
    return target


def test_every_module_belongs_to_one_unit():
    loose = sorted(n for n in modules() if n not in ENTRY and unit_of(n) is None)
    assert not loose, f"modules outside every unit (add them to LAYERS): {loose}"


def test_imports_follow_the_layers():
    known = modules()
    wrong = []
    for name, path in known.items():
        unit = unit_of(name)
        for target, line in imports(name, path):
            if not target.startswith("tc002"):
                continue
            target = _resolve(target, known)
            if unit is None:  # the entry modules may start the CLI, nothing else
                ok = unit_of(target) == "cli" or target == "tc002"
            else:
                ok = target == "tc002" or _allowed(unit, target)
            if not ok:
                wrong.append(f"{path.relative_to(ROOT)}:{line} {unit} -> {target}")
    assert not wrong, "imports against the layers:\n" + "\n".join(sorted(set(wrong)))


def test_layers_only_point_down():
    order = list(LAYERS)
    for unit, (_, allowed) in LAYERS.items():
        for target in allowed:
            below = unit_of("tc002." + target)
            assert order.index(below) > order.index(unit), f"{unit} may import {target} above it"


def test_only_the_standard_library_is_imported():
    stdlib = set(sys.stdlib_module_names)
    third_party = []
    for name, path in modules().items():
        for target, line in imports(name, path):
            top = target.split(".")[0]
            if top and top != "tc002" and top not in stdlib:
                third_party.append(f"{path.relative_to(ROOT)}:{line} {target}")
    assert not third_party, "tc002 has no runtime dependencies:\n" + "\n".join(third_party)


def test_front_ends_do_no_io_of_their_own():
    wrong = []
    for name, path in modules().items():
        if unit_of(name) not in FRONT_ENDS:
            continue
        for target, line in imports(name, path):
            if any(target == f or target.startswith(f + ".") for f in FRONT_END_FORBIDDEN):
                wrong.append(f"{path.relative_to(ROOT)}:{line} {target}")
    assert not wrong, "front ends ask App instead:\n" + "\n".join(sorted(set(wrong)))


def test_no_import_cycles_between_modules():
    known = modules()
    graph = {
        name: {
            t
            for target, _ in imports(name, path)
            if target.startswith("tc002") and (t := _resolve(target, known)) != name
        }
        for name, path in known.items()
    }
    # a package's __init__ re-exporting its own modules is not a cycle worth refusing
    for name in graph:
        graph[name] = {t for t in graph[name] if not (name.startswith(t + ".") and t in known)}
    seen, stack, cycles = set(), [], []

    def visit(node):
        if node in stack:
            cycles.append(" -> ".join([*stack[stack.index(node) :], node]))
            return
        if node in seen:
            return
        seen.add(node)
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            visit(nxt)
        stack.pop()

    for node in sorted(graph):
        visit(node)
    assert not cycles, "import cycles:\n" + "\n".join(cycles)


def render():
    """The table docs/architecture.md shows between its `layers` markers."""
    lines = ["| Unit | Owns | May import |", "|---|---|---|"]
    for unit, (owns, allowed) in LAYERS.items():
        target = ", ".join(f"`{a}`" for a in allowed) or "—"
        lines.append(f"| `{unit}/` | {owns} | {target} |")
    return "\n".join(lines)


def test_the_documented_layers_are_these():
    text = DOC.read_text()
    start, end = "<!-- layers:start -->\n", "\n<!-- layers:end -->"
    assert start in text and end in text, "docs/architecture.md lost its layers markers"
    shown = text.split(start, 1)[1].split(end, 1)[0]
    assert shown == render(), (
        "docs/architecture.md is stale: paste `uv run python tests/test_architecture.py`"
    )


if __name__ == "__main__":
    print(render())
