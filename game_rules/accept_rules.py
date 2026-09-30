"""Match accept policy (no Qt, no I/O, no network)."""

READY_CHECK_COOLDOWN = 15.0  # one client prompt never outlives this

GAME_ACTIVE_PHASES = ("ChampSelect", "GameStart", "InProgress", "InGame", "Reconnect")


def should_accept(data, last_accept_ts, now, cooldown=READY_CHECK_COOLDOWN):
    if not isinstance(data, dict) or data.get("state") != "InProgress":
        return False
    # Already answered this prompt — never accept twice.
    if data.get("playerResponse") in ("Accepted", "Declined"):
        return False
    if now - last_accept_ts < cooldown:
        return False
    return True
