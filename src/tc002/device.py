"""HTTP client for the TC002 stock firmware's local API.

Endpoints follow Ulanzi's protocol reference
(github.com/UlanziTechnology/Ulanzi-U-Clock-TC002/tree/main/protocol).
"""

import json
import urllib.error
import urllib.parse
import urllib.request

# The clock is always on the LAN; an HTTP_PROXY (e.g. a local Clash on :7890) cannot
# reach it and makes every request hang, so this client never uses a proxy.
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# Built-in app categories whose config carries per-app `enable` flags and an order.
CATEGORY_ENDPOINTS = {
    "tools": ("/getToolsConfig", "/setToolsConfig", "toolsInfos", "toolsOrder"),
    "social": ("/getSocial", "/setSocial", "socialInfos", "socialOrder"),
    "calendar": ("/getCalendar", "/setCalendar", "calendarInfos", "calendarOrder"),
}


class DeviceError(RuntimeError):
    """The clock was unreachable (`status` None) or answered with an HTTP error `status`."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class Device:
    """One TC002 on the LAN, addressed by IP or host name."""

    def __init__(self, host, timeout=5):
        self.base = f"http://{host}"
        self.timeout = timeout

    def _request(self, path, body=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            self.base + path,
            data=data,
            method=method or ("GET" if body is None else "POST"),
            headers={"Content-Type": "application/json"},
        )
        # The clock's Wi-Fi power saving can drop the first request after idle; retry once.
        for attempt in (1, 2):
            try:
                with _DIRECT.open(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                break
            except urllib.error.HTTPError as exc:
                raise DeviceError(
                    f"{self.base}{path}: HTTP {exc.code} {exc.reason}", exc.code
                ) from exc
            except (urllib.error.URLError, OSError) as exc:
                if attempt == 2:
                    raise DeviceError(f"{self.base}{path}: {exc}") from exc
        try:
            reply = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise DeviceError(f"{self.base}{path}: non-JSON reply {raw[:80]!r}") from exc
        if isinstance(reply, dict) and reply.get("code") not in (None, 200):
            raise DeviceError(f"{self.base}{path}: device rejected request: {reply}")
        return reply

    # -- custom (DIY) apps ------------------------------------------------------

    def push(self, app, frame):
        """Create or replace the custom app `app` with `frame` (text/image/draw)."""
        return self._request("/api/custom?name=" + urllib.parse.quote(app), frame)

    def remove(self, app):
        """An empty body deletes the custom app."""
        return self.push(app, {})

    def apps(self):
        return self._request("/api/customList").get("apps", [])

    def switch_custom(self, app):
        """Bring a custom app to the screen (firmware V1.1.0+)."""
        return self._request("/api/switchDiyApp?name=" + urllib.parse.quote(app), method="POST")

    # -- built-in apps ----------------------------------------------------------

    def switch_builtin(self, category, index):
        return self._request("/switchApp", {"type": category, "index": index})

    def category_config(self, category):
        """Full config of a built-in category, e.g. tools → toolsInfos + toolsOrder."""
        get_path, _, _, _ = CATEGORY_ENDPOINTS[category]
        return self._request(get_path)

    def set_category_config(self, category, body):
        _, set_path, _, _ = CATEGORY_ENDPOINTS[category]
        return self._request(set_path, body)

    # -- device -----------------------------------------------------------------

    def config(self):
        return self._request("/getConfig")

    def set_config(self, **fields):
        """Merge `fields` into the global config (brightness, carouselSpeed, ...)."""
        return self._request("/setConfig", fields)

    def info(self):
        return {"base": self._request("/getBase"), "config": self.config()}
