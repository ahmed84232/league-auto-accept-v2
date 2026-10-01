"""Session manager: pure game-result bookkeeping (no Qt, no file I/O).

QmlBridge keeps rendering + persistence; this class owns the rules for
wins/losses, lp_delta accumulation, pending backfills and history entries
so they can be unit-tested without a GUI.
"""

from client_api import history_store
from client_api import session_store


class SessionManager:
    def __init__(self, session=None, history=None, pending=None, max_history=200):
        self.session = dict(session) if session is not None else session_store.default_session()
        self.history = list(history) if history is not None else []
        self.pending = dict(pending) if pending is not None else {}
        self.max_history = max_history

    def reset_session(self):
        self.session = session_store.default_session()
        return self.session

    def apply_game_result(self, result, now=None):
        result = result or {}
        logs = []
        if result.get("remake"):
            self.session["remakes"] = self.session.get("remakes", 0) + 1
            logs.append(("Remake detected — result not counted.", "warning"))
        else:
            outcome = result.get("result")
            if outcome == "win":
                self.session["wins"] += 1
                if result.get("pending"):
                    logs.append(("Victory! LP pending — will backfill.", "success"))
                else:
                    logs.append(("Victory! Session updated.", "success"))
            elif outcome == "loss":
                self.session["losses"] += 1
                if result.get("pending"):
                    logs.append(("Defeat. LP pending — will backfill.", "warning"))
                else:
                    logs.append(("Defeat. Session updated.", "warning"))
            else:
                logs.append(("Game over — result could not be determined.", "warning"))

        delta = result.get("lp_delta")
        if not result.get("remake") and delta is not None:
            self.session["lp_delta"] += delta

        game_id = result.get("game_id")
        if game_id is not None and result.get("pending") and not result.get("remake"):
            # Provisional was None — correction will add the real delta later.
            self.pending[game_id] = delta

        post = result.get("post")
        if post:
            self.session["tier"] = post.get("tier")
            self.session["division"] = post.get("division")
            self.session["lp"] = post.get("lp")

        entry = history_store.build_entry(result, now=now)
        self.history = (self.history + [entry])[-self.max_history:]
        return {"logs": logs, "history_entry": entry}

    def apply_correction(self, result):
        result = result or {}
        game_id = result.get("game_id")
        delta = result.get("lp_delta")
        if game_id not in self.pending:
            return {"handled": False, "logs": []}
        provisional = self.pending.pop(game_id, None)
        if delta is None:
            return {"handled": False, "logs": []}
        if provisional is not None:
            delta_diff = delta - provisional
        else:
            delta_diff = delta
        self.session["lp_delta"] += delta_diff

        post = result.get("post")
        if post:
            self.session["tier"] = post.get("tier")
            self.session["division"] = post.get("division")
            self.session["lp"] = post.get("lp")

        updated = False
        for entry in reversed(self.history):
            if entry.get("game_id") == game_id:
                entry["lp"] = delta
                updated = True
                break
        if not updated and self.history:
            self.history[-1]["lp"] = delta
            self.history[-1].setdefault("game_id", game_id)

        return {"handled": True, "logs": [(f"LP backfilled  ({delta:+d} LP)", "success")]}

    def apply_manual_adjustment(self, lp_delta, now=None):
        """Record a hand-entered LP change (late Riot adjustments, fixes).

        Sign decides the outcome: positive counts a win, negative a loss.
        Rank tier/division/LP are untouched — only counters move.
        """
        if (isinstance(lp_delta, bool) or not isinstance(lp_delta, int)
                or lp_delta == 0):
            return {"handled": False, "logs": []}
        outcome = "win" if lp_delta > 0 else "loss"
        if outcome == "win":
            self.session["wins"] = self.session.get("wins", 0) + 1
            level = "success"
        else:
            self.session["losses"] = self.session.get("losses", 0) + 1
            level = "warning"
        self.session["lp_delta"] = self.session.get("lp_delta", 0) + lp_delta

        entry = history_store.build_entry(
            {"result": outcome, "remake": False,
             "lp_delta": lp_delta, "game_id": None},
            now=now,
        )
        self.history = (self.history + [entry])[-self.max_history:]
        word = "Victory" if outcome == "win" else "Defeat"
        return {"handled": True,
                "logs": [(f"Manual fix: {word} ({lp_delta:+d} LP) recorded.",
                          level)]}


# Backwards-compatible alias (old name).
SessionViewModel = SessionManager
