"""Run `tc002 watch` as a launchd agent: starts at login, restarts if it dies."""

import os
import plistlib
import subprocess
import time
from pathlib import Path

LABEL = "dev.tc002.watch"
PLIST = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
LOG = Path.home() / "Library/Logs/tc002.log"


def _domain():
    return f"gui/{os.getuid()}"


def _launchctl(*args, check=True):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, check=check)


def plist(executable):
    return {
        "Label": LABEL,
        "ProgramArguments": [executable, "watch"],  # screens + playlist come from tc002.toml
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "ProcessType": "Background",
        "StandardOutPath": str(LOG),
        "StandardErrorPath": str(LOG),
        # ps, iostat, vm_stat and sysctl live here; launchd's default PATH is minimal.
        "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    }


def _stop(timeout=10):
    """Boot the agent out and wait until launchd has really dropped it.

    bootout returns before the old process exits; bootstrapping in that window fails
    with "Bootstrap failed: 5: Input/output error".
    """
    _launchctl("bootout", f"{_domain()}/{LABEL}", check=False)  # absent on first install
    deadline = time.monotonic() + timeout
    while _launchctl("print", f"{_domain()}/{LABEL}", check=False).returncode == 0:
        if time.monotonic() > deadline:
            raise RuntimeError(f"{LABEL} did not stop within {timeout}s")
        time.sleep(0.2)


def install(executable):
    """Write the agent for the installed `tc002` executable and (re)load it."""
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    _stop()
    PLIST.write_bytes(plistlib.dumps(plist(executable)))
    _launchctl("bootstrap", _domain(), str(PLIST))
    return executable


def restart():
    """Restart the running agent so it re-reads tc002.toml; no-op when not installed."""
    if _launchctl("print", f"{_domain()}/{LABEL}", check=False).returncode != 0:
        return False
    _launchctl("kickstart", "-k", f"{_domain()}/{LABEL}")
    return True


def uninstall():
    """Stop the agent (its SIGTERM handler clears the clock) and delete the plist."""
    _stop()
    PLIST.unlink(missing_ok=True)


def status():
    result = _launchctl("print", f"{_domain()}/{LABEL}", check=False)
    if result.returncode != 0:
        return "not installed"
    fields = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.strip().partition(" = ")
        if sep and key in ("state", "pid", "last exit code", "runs"):
            fields.setdefault(key, value)
    return ", ".join(f"{k}: {v}" for k, v in fields.items()) + f"\nlog: {LOG}"
