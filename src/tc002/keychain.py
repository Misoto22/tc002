"""Secrets for connections (tokens, private URLs), kept in the macOS login Keychain.

Values never pass through a command line (where other processes could read them): they
are written by `security -i`, which reads its command from stdin. A value that is an
`op://` reference is stored as is and resolved with 1Password's `op read` when used.
Nothing here prints, logs or returns a secret except `get` to its caller.
"""

import subprocess

SERVICE = "tc002"
TIMEOUT = 10


def _quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def save(name, value, run=subprocess.run):
    if not value or "\n" in value:
        raise ValueError("a secret is one non-empty line")
    command = f"add-generic-password -U -s {SERVICE} -a {_quote(name)} -w {_quote(value)}\n"
    done = run(["security", "-i"], input=command, capture_output=True, text=True, timeout=TIMEOUT)
    if done.returncode != 0 or "error" in (done.stdout + done.stderr).lower():
        raise OSError("the Keychain did not accept the value")


def get(name, run=subprocess.run):
    """The secret, resolved if it is an op:// reference; None when none is saved."""
    done = run(
        ["security", "find-generic-password", "-s", SERVICE, "-a", name, "-w"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    if done.returncode != 0:
        return None
    value = done.stdout.rstrip("\n")
    if value.startswith("op://"):
        resolved = run(["op", "read", value], capture_output=True, text=True, timeout=TIMEOUT)
        if resolved.returncode != 0:
            raise OSError("1Password could not read the reference")
        return resolved.stdout.rstrip("\n")
    return value


def has(name, run=subprocess.run):
    done = run(
        ["security", "find-generic-password", "-s", SERVICE, "-a", name],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    return done.returncode == 0


def delete(name, run=subprocess.run):
    run(
        ["security", "delete-generic-password", "-s", SERVICE, "-a", name],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
