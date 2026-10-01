"""Session persistence (no Qt). Format-compatible with session.json."""

import json


def default_session():
    return {"wins": 0, "losses": 0, "remakes": 0, "lp_delta": 0, "tier": None, "division": None, "lp": None}


def load_session(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        session = default_session()
        session.update({k: data[k] for k in session if k in data})
        return session
    except (OSError, ValueError, TypeError):
        return default_session()


def save_session(session, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)
    except OSError:
        pass
