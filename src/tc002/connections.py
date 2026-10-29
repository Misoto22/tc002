"""Services the API screens connect to: which settings each needs, and where they live.

Plain settings (a Home Assistant address) go in tc002.toml `[connections.<name>]`;
secrets (tokens, private calendar links) go in the Keychain under "<name>.<field>"
(keychain.py), never in a file. Public services need no connection at all.
"""

from . import keychain

# name: {field: secret?}
CONNECTIONS = {
    "homeassistant": {"url": False, "token": True},
    "calendar": {"ics_url": True},
}


def secret_name(connection, field):
    return f"{connection}.{field}"


def validate(data):
    """Problems with the [connections.*] tables (empty when fine)."""
    problems = []
    for name, values in data.items():
        fields = CONNECTIONS.get(name)
        if fields is None:
            problems.append(f"connections.{name}: unknown connection; known {sorted(CONNECTIONS)}")
            continue
        for key, value in values.items():
            if key not in fields:
                problems.append(f"connections.{name}.{key} is not a setting of this connection")
            elif fields[key]:
                problems.append(f"connections.{name}.{key} is a secret: save it in tc002 ui")
            elif not isinstance(value, str):
                problems.append(f"connections.{name}.{key} must be text")
    return problems


def value(settings, connection, field, store=keychain):
    """A connection's setting: from the Keychain when secret, else from tc002.toml."""
    if CONNECTIONS[connection][field]:
        return store.get(secret_name(connection, field))
    return ((settings.connections if settings else {}).get(connection) or {}).get(field)


def status(settings, store=keychain):
    """For the UI: each connection's plain values and which secrets are saved (never them)."""
    out = {}
    for name, fields in CONNECTIONS.items():
        out[name] = {
            field: {"secret": True, "saved": store.has(secret_name(name, field))}
            if secret
            else {"secret": False, "value": value(settings, name, field, store)}
            for field, secret in fields.items()
        }
    return out
