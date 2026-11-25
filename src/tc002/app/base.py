"""What every use case stands on: which clock and which tc002.toml, the clock client,
the settings as they are on disk now, and the one place lower-level errors become
`app.errors` (`guarded`), so front ends never see a DeviceError or a ConfigError."""

import functools
import inspect
import subprocess

from .. import config
from ..clock.device import Device, DeviceError
from ..clock.provision import ProvisionError
from ..config import writer
from ..render import themes
from .errors import (
    AppError,
    ClockUnreachable,
    CommandFailed,
    InvalidRequest,
    InvalidSettings,
    NotConfigured,
)


def translate(exc):
    """The AppError a lower-level failure means, or None to let it through."""
    if isinstance(exc, DeviceError):
        return ClockUnreachable(str(exc), exc.status)
    if isinstance(exc, config.ConfigError):
        return InvalidSettings("Invalid tc002.toml", f"{exc}. Fix the file, then try again.")
    if isinstance(exc, ProvisionError):
        return InvalidRequest("Invalid settings", str(exc))
    if isinstance(exc, subprocess.SubprocessError):
        # launchctl / open failing: say what it printed
        stderr = (getattr(exc, "stderr", None) or "").strip()
        return CommandFailed("Command failed", f"{exc}: {stderr}" if stderr else str(exc))
    return None


def _guard(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except AppError:
            raise
        except Exception as exc:
            mapped = translate(exc)
            if mapped is None:
                raise
            raise mapped from exc

    return wrapper


def guarded(cls):
    """Run every public method of `cls` through `translate`."""
    for name, member in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("_"):
            setattr(cls, name, _guard(member))
    return cls


class Base:
    """One clock (`host`) and one tc002.toml (`config_path`).

    `preview_dir` sends text, alerts and screens to LED mock-up GIFs instead of
    the clock. `device` is a factory for the clock client, for tests (by default a
    `Device(host, timeout)`).
    """

    def __init__(
        self,
        host=None,
        config_path=None,
        state_dir=None,
        *,
        timeout=5,
        preview_dir=None,
        device=None,
    ):
        self.host, self.config_path = host, config_path
        self.state_dir = state_dir or config.STATE_DIR
        self.timeout, self.preview_dir = timeout, preview_dir
        self._device_factory = device

    @classmethod
    def local(cls, host=None, config_path=None, **kwargs):
        """The clock and tc002.toml this Mac was set up with (`tc002 setup`, $TC002_*),
        unless `host` or `config_path` say otherwise."""
        return cls(config.host(host), config_path or config.path(), **kwargs)

    def device(self):
        """The clock client. Raises NotConfigured when no clock was set up."""
        if self._device_factory:
            return self._device_factory()
        if not self.host:
            raise NotConfigured("No clock configured", "Run `tc002 setup --host <IP>` first.")
        return Device(self.host, timeout=self.timeout)

    def settings(self):
        """tc002.toml as it is on disk now (built-in defaults when there is none)."""
        return config.load(self.config_path)

    def settings_or_none(self):
        try:
            return self.settings()
        except config.ConfigError:
            return None

    def config_version(self):
        """A fingerprint of tc002.toml on disk; pass it back to save_config as `expected`."""
        return writer.version(self.config_path) if self.config_path else None

    def led_theme(self):
        """The saved LED theme; classic until a readable tc002.toml says otherwise."""
        settings = self.settings_or_none()
        return settings.led_theme if settings else themes.CLASSIC

    def _need_config_file(self):
        if not self.config_path:
            raise NotConfigured("No tc002.toml", "Run `tc002 setup --config <path>` first.")

    def _parse(self, data, source=None):
        try:
            return config.parse(data, source or str(self.config_path))
        except config.ConfigError as exc:
            problems = str(exc).split(": ", 1)[-1].split("; ")
            raise InvalidSettings(
                "Invalid settings",
                "tc002.toml was not changed.",
                [{"field": "config", "message": p} for p in problems],
            ) from None
