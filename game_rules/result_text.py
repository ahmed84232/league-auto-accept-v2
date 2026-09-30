"""Ranked game-outcome decision (no Qt, no I/O, no network).

Pure function so the exact Victory/Defeat/remake/LP-pending strings
and payload shape can be unit-tested without a League client.
"""

from game_rules import rank_math


def decide_game_outcome(pre, post, eog, game_id):
    remake = bool(eog and (eog.get("game_length") or 0) < 300)
    win = None if remake else (eog.get("win") if eog else None)

    resolved = post is not None and (
        pre is None or rank_math.stats_changed(pre, post)
    )
    if pre is None or resolved:
        delta = rank_math.lp_delta(pre, post)
        pending = False
    else:
        # Client hasn't refreshed ranked stats yet — never emit false 0.
        delta = None
        pending = True

    if remake:
        text = "Game over — remake, result not counted"
    elif win is True:
        text = "Victory!"
        if delta is not None:
            text += f"  ({delta:+d} LP)"
        elif pending:
            text += "  (LP pending...)"
    elif win is False:
        text = "Defeat"
        if delta is not None:
            text += f"  ({delta:+d} LP)"
        elif pending:
            text += "  (LP pending...)"
    else:
        text = "Game over — result unknown"

    level = "success" if win else "warning"
    payload = {
        "result": "win" if win is True else "loss" if win is False else "unknown",
        "remake": remake,
        "lp_delta": delta,
        "post": post,
        "game_id": game_id,
        "pending": pending,
    }
    return {
        "remake": remake,
        "win": win,
        "resolved": resolved,
        "lp_delta": delta,
        "pending": pending,
        "text": text,
        "level": level,
        "payload": payload,
    }
