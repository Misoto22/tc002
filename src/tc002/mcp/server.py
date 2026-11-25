"""`tc002 mcp`: a Model Context Protocol server over stdio, standard library only.

One JSON-RPC 2.0 message per line on stdin, one reply per line on stdout (the MCP stdio
transport). It answers `initialize`, `ping`, `tools/list`, `tools/call`,
`resources/list` and `resources/read`; everything a tool does is an `App` method
(`tools.py`). Anything else the code prints goes to stderr, so stdout carries protocol
messages only.
"""

import json
import sys
from importlib.metadata import version

from ..app import AppError
from .tools import TOOLS

PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = """\
tc002 controls one Ulanzi TC002 pixel clock (52x16 LEDs) on the local network.
Call get_status first. Read-only tools change nothing; show_screen, send_message,
screen_off/on and the focus timer are temporary; set_display, save_config,
apply_layout and restore_layout change tc002.toml or the clock's settings for good.
"""

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS = -32700, -32600, -32601, -32602

RESOURCES = {
    "tc002://status": ("Clock status", "get_status"),
    "tc002://screens": ("Screens and built-in apps", "list_screens"),
    "tc002://config": ("tc002.toml as JSON", "get_config"),
}


class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def check(schema, value, where="arguments"):
    """The few JSON Schema rules the tools use; returns a problem or None."""
    if "enum" in schema and value not in schema["enum"]:
        return f"{where} must be one of {schema['enum']}"
    kind = schema.get("type")
    types = {
        "object": dict,
        "string": str,
        "boolean": bool,
        "integer": int,
        "number": (int, float),
    }
    if kind and not isinstance(value, types[kind]):
        return f"{where} must be a{'n' if kind[0] in 'aeiou' else ''} {kind}"
    if kind in ("integer", "number") and isinstance(value, bool):
        return f"{where} must be a{'n' if kind[0] in 'aeiou' else ''} {kind}"
    if "minimum" in schema and value < schema["minimum"]:
        return f"{where} must be at least {schema['minimum']}"
    if "maximum" in schema and value > schema["maximum"]:
        return f"{where} must be at most {schema['maximum']}"
    if kind == "string":
        if len(value) < schema.get("minLength", 0):
            return f"{where} must not be empty"
        if len(value) > schema.get("maxLength", len(value)):
            return f"{where} must be at most {schema['maxLength']} characters"
    if kind == "object":
        props = schema.get("properties", {})
        for name in schema.get("required", ()):
            if name not in value:
                return f"{where}.{name} is required"
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(props))
            if extra:
                return f"{where} has unknown keys {extra}; allowed: {sorted(props)}"
        if len(value) < schema.get("minProperties", 0):
            return f"{where} needs at least one key"
        for name, item in value.items():
            if name in props and (problem := check(props[name], item, f"{where}.{name}")):
                return problem
    return None


def _result(value, error=False):
    structured = value if isinstance(value, dict) else {"result": value}
    text = json.dumps(structured, ensure_ascii=False, indent=1, default=str)
    out = {"content": [{"type": "text", "text": text}], "isError": error}
    if not error:
        out["structuredContent"] = structured
    return out


def _failure(text):
    return {"content": [{"type": "text", "text": text}], "isError": True}


class Server:
    def __init__(self, app):
        self.app = app
        self.methods = {
            "initialize": self.initialize,
            "ping": lambda params: {},
            "tools/list": lambda params: {"tools": [t.describe() for t in TOOLS.values()]},
            "tools/call": self.call_tool,
            "resources/list": self.list_resources,
            "resources/read": self.read_resource,
        }

    def initialize(self, params):
        asked = params.get("protocolVersion")
        return {
            "protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}, "resources": {}},
            "serverInfo": {"name": "tc002", "title": "TC002 pixel clock", "version": _version()},
            "instructions": INSTRUCTIONS,
        }

    def call_tool(self, params):
        name, args = params.get("name"), params.get("arguments") or {}
        tool = TOOLS.get(name)
        if tool is None:
            raise RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        if problem := check(tool.input_schema, args):
            return _failure(f"Invalid arguments: {problem}")
        try:
            return _result(tool.run(self.app, args))
        except AppError as exc:
            lines = [f"{exc.title}: {exc.detail}"]
            lines += [e["message"] for e in exc.errors or ()]
            return _failure("\n".join(lines))
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _failure(f"{type(exc).__name__}: {exc}")

    def list_resources(self, params):
        return {
            "resources": [
                {"uri": uri, "name": tool, "title": title, "mimeType": "application/json"}
                for uri, (title, tool) in RESOURCES.items()
            ]
        }

    def read_resource(self, params):
        uri = params.get("uri")
        if uri not in RESOURCES:
            raise RpcError(INVALID_PARAMS, f"Unknown resource: {uri}")
        result = self.call_tool({"name": RESOURCES[uri][1]})
        return {
            "contents": [
                {"uri": uri, "mimeType": "application/json", "text": result["content"][0]["text"]}
            ]
        }

    def handle(self, message):
        """One decoded message in, the reply (or None for a notification) out."""
        if not isinstance(message, dict):
            return _error(None, INVALID_REQUEST, "Expected a JSON-RPC 2.0 object")
        if message.get("jsonrpc") != "2.0":
            return _error(message.get("id"), INVALID_REQUEST, "Expected a JSON-RPC 2.0 object")
        mid, method = message.get("id"), message.get("method")
        if "id" not in message:  # a notification (initialized, cancelled): no reply
            return None
        if not isinstance(method, str):
            return _error(mid, INVALID_REQUEST, "Missing method")
        handler = self.methods.get(method)
        if handler is None:
            return _error(mid, METHOD_NOT_FOUND, f"Method not found: {method}")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error(mid, INVALID_PARAMS, "params must be an object")
        try:
            return {"jsonrpc": "2.0", "id": mid, "result": handler(params)}
        except RpcError as exc:
            return _error(mid, exc.code, exc.message)

    def handle_line(self, line):
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            return _error(None, PARSE_ERROR, f"Parse error: {exc}")
        if isinstance(message, list):  # batches (2025-03-26 only): answer each
            replies = [r for m in message if (r := self.handle(m)) is not None]
            return replies or None
        return self.handle(message)


def _error(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def _version():
    try:
        return version("tc002")
    except Exception:  # noqa: BLE001 - running from a checkout without metadata
        return "0"


def serve(app, stdin=None, stdout=None):
    """Answer messages until stdin closes."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    real_stdout, sys.stdout = sys.stdout, sys.stderr  # stray prints must not break the stream
    server = Server(app)
    try:
        for line in stdin:
            if not line.strip():
                continue
            reply = server.handle_line(line)
            if reply is not None:
                stdout.write(json.dumps(reply, ensure_ascii=False, default=str) + "\n")
                stdout.flush()
    finally:
        sys.stdout = real_stdout
