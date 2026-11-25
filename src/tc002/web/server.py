"""Local HTTP server for `tc002 ui`: static files plus the JSON API.

Bound to 127.0.0.1 only. Because a page on any website can still send requests to
localhost, every request must carry a Host header naming this server (blocks DNS
rebinding) and every write must carry the per-process token embedded in index.html
(blocks cross-site requests, which cannot read that page).
"""

import json
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qsl, urlsplit

from ..app import AppError, catalog
from . import api
from .errors import ApiError, problem_of

MAX_BODY = 256 * 1024
LOOPBACK = "127.0.0.1"  # the UI never listens beyond this machine
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "text/javascript",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".json": "application/json",
    ".md": "text/plain; charset=utf-8",
}
STATIC = resources.files("tc002.web").joinpath("static")


def _static_files(root, prefix=""):
    """Every file under static/, keyed by its URL path; nothing else is ever served."""
    files = {}
    for entry in root.iterdir():
        if entry.is_dir():
            files |= _static_files(entry, f"{prefix}{entry.name}/")
        elif entry.is_file():
            files[prefix + entry.name] = entry
    return files


def problem(status, title, detail, errors=None, instance=None):
    body = {
        "type": f"https://tc002.local/errors/{title.lower().replace(' ', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if instance:
        body["instance"] = instance
    if errors:
        body["errors"] = errors
    return body


def make_handler(app, token, port):
    allowed_hosts = {f"{LOOPBACK}:{port}", f"localhost:{port}"}
    static_files = _static_files(STATIC)

    class Handler(BaseHTTPRequestHandler):
        server_version = "tc002"

        def log_message(self, fmt, *args):  # keep the terminal quiet; errors are returned
            pass

        def _send(self, status, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'",
            )
            self.end_headers()
            self.wfile.write(data)

        def _fail(self, status, title, detail, errors=None):
            self._send(
                status,
                problem(status, title, detail, errors, self.path),
                "application/problem+json",
            )

        def _guard(self, write):
            if self.headers.get("Host") not in allowed_hosts:
                self._fail(421, "Wrong host", f"Open the UI at http://{LOOPBACK}:{port}.")
                return False
            token_ok = secrets.compare_digest(self.headers.get("X-TC002-Token", ""), token)
            # A read can still have side effects (discover scans the LAN, a preview runs a
            # screen) or leak timing, so a browser's cross-site request for /api/* is refused
            # too. Browsers always send Sec-Fetch-Site; tools like curl send none and are
            # not a cross-site threat.
            fetch_site = self.headers.get("Sec-Fetch-Site")
            if (
                not write
                and self.path.startswith("/api/")
                and fetch_site not in (None, "same-origin", "none")
                and not token_ok
            ):
                self._fail(403, "Cross-site request", "Requests must come from the tc002 UI.")
                return False
            if write:
                origin = self.headers.get("Origin")
                if origin and urlsplit(origin).netloc not in allowed_hosts:
                    self._fail(403, "Cross-site request", "Requests must come from the tc002 UI.")
                    return False
                if not token_ok:
                    self._fail(403, "Missing token", "Reload the page and try again.")
                    return False
            return True

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ApiError(413, "Too large", f"Requests are limited to {MAX_BODY} bytes.")
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError as exc:
                raise ApiError(400, "Malformed JSON", str(exc)) from None
            if not isinstance(data, dict):
                raise ApiError(400, "Malformed JSON", "Expected a JSON object.")
            return data

        def _dispatch(self, method):
            url = urlsplit(self.path)
            if not self._guard(write=method != "GET"):
                return
            try:
                if method == "GET":
                    self._get(url)
                else:
                    self._post(url.path, self._body())
            except ApiError as exc:
                self._fail(exc.status, exc.title, exc.detail, exc.errors)
            except AppError as exc:
                self._fail(*problem_of(exc))
            except (OSError, RuntimeError, ValueError) as exc:
                self._fail(500, "Request failed", str(exc))

        def _get(self, url):
            path = url.path
            query = dict(parse_qsl(url.query))
            start, end = api.PREVIEW
            if path in api.GETS:
                self._send(200, api.get(app, path, query))
            elif path.startswith(start) and path.endswith(end):
                name = path.removeprefix(start).removesuffix(end)
                self._send(200, api.preview(app, name, query), "image/gif")
            elif path in ("/", "/index.html"):
                html = static_files["index.html"].read_text().replace("{{TOKEN}}", token)
                self._send(200, html.encode(), TYPES[".html"])
            elif (name := path.lstrip("/")) in static_files and name != "index.html":
                suffix = "." + name.rsplit(".", 1)[-1]
                self._send(200, static_files[name].read_bytes(), TYPES.get(suffix, "text/plain"))
            else:
                self._fail(404, "Not found", f"No resource at {path}.")

        def _post(self, path, body):
            self._send(HTTPStatus.OK, api.post(app, path, body, self.headers))

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

    return Handler


def serve(app, port=catalog.UI_PORT, ready=None):
    """Serve `app` until interrupted. `ready(url)` is called once the socket is listening."""
    token = secrets.token_urlsafe(24)
    httpd = ThreadingHTTPServer((LOOPBACK, port), BaseHTTPRequestHandler)
    # port 0 picks a free port; the Host check must use the real one
    httpd.RequestHandlerClass = make_handler(app, token, httpd.server_port)
    url = f"http://{LOOPBACK}:{httpd.server_port}/"
    app.warm_previews()  # draw the fixed previews while the browser opens
    if ready:
        ready(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
