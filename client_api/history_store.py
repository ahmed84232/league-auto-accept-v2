"""LP history persistence (no Qt). Format-compatible with history.json."""

import json
from datetime import datetime


def load_history(path, max_history=200):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [e for e in data if isinstance(e, dict)][-max_history:]
    except (OSError, ValueError, TypeError):
        pass
    return []


def save_history(history, path, max_history=200):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history[-max_history:], f, indent=2)
    except OSError:
        pass


def build_entry(result, now=None):
    is_remake = bool((result or {}).get("remake"))
    ts = (now or datetime.now()).isoformat(timespec="seconds")
    return {
        "ts": ts,
        # Remakes never carry LP — None renders as "—".
        "lp": None if is_remake else (result or {}).get("lp_delta"),
        "result": "remake" if is_remake else (result or {}).get("result"),
        "game_id": (result or {}).get("game_id"),
    }


def append_history(history, result, max_history=200, now=None):
    updated = list(history or []) + [build_entry(result, now=now)]
    return updated[-max_history:]
