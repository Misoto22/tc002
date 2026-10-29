"""Small HTTP GETs to public services, for screens that show data from the internet.

Errors surface as OSError or ValueError, which a screen's sampling loop turns into the
"data is old" state (runtime/freshness.py) instead of a crash. Nothing here reaches the
clock: that client lives in device.py and never uses a proxy; these calls do follow the
system's proxy settings, as any other app on the Mac would.
"""

import json
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version

TIMEOUT = 10

try:
    AGENT = f"tc002/{version('tc002')} (+https://github.com/Misoto22/tc002)"
except PackageNotFoundError:
    AGENT = "tc002"


def get(url, headers=None, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise OSError(f"{urllib.request.urlparse(url).netloc}: HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise OSError(f"{urllib.request.urlparse(url).netloc}: {exc.reason}") from None


def get_json(url, headers=None, timeout=TIMEOUT):
    return json.loads(get(url, headers, timeout))
