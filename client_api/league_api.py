"""Pure LCU payload parsing (no Qt, no I/O, no network).

Network loops, retries, sleeps and logging stay in worker.py;
this module only turns already-fetched JSON into values so it
can be unit-tested without a League client.
"""

import requests


def build_session(auth_token=""):
    session = requests.Session()
    session.verify = False
    session.headers["Accept"] = "application/json"
    if auth_token:
        session.headers["Authorization"] = f"Basic {auth_token}"
    return session


def base_url(port):
    return f"https://127.0.0.1:{port}"


def queue_id_from_session(data):
    if not data:
        return None
    game_data = data.get("gameData") or {}
    queue_id = game_data.get("queueId")
    if queue_id is None:
        queue_id = (game_data.get("queue") or {}).get("id")
    return queue_id


def session_context_from_session(data):
    if not data:
        return None, None
    game_data = data.get("gameData") or {}
    return queue_id_from_session(data), game_data.get("gameId")


def summoner_id_from_summoner(data):
    if not data:
        return None
    return str(data.get("summonerId", ""))


def ranked_entry_from_data(data, queue_name):
    if not data:
        return None
    entry = (data.get("queueMap") or {}).get(queue_name)
    if not entry:
        entry = data.get("highestRankedEntrySR") or data.get("highestRankedEntry")
    return entry


def normalize_ranked_entry(entry):
    if not entry:
        return None
    return {
        "tier": entry.get("tier"),
        "division": entry.get("division"),
        "lp": entry.get("leaguePoints"),
        "wins": entry.get("wins"),
        "losses": entry.get("losses"),
    }


def queue_keys(data):
    return list((data.get("queueMap") or {}).keys())


def eog_result_from_data(data, summoner_id):
    """Returns (result, needs_fallback_log). result is None if undetermined."""
    if data is None:
        return None, False
    game_length = (
        data.get("gameLength")
        or (data.get("gameData") or {}).get("gameLength")
        or 0
    )

    local = data.get("localPlayer") or {}
    local_stats = local.get("stats") or {}
    if local_stats.get("WIN") == 1:
        return {"win": True, "game_length": game_length}, False
    if local_stats.get("LOSE") == 1:
        return {"win": False, "game_length": game_length}, False

    for team in data.get("teams") or []:
        if team.get("isPlayerTeam"):
            return {"win": bool(team.get("isWinningTeam")), "game_length": game_length}, False

    for player in data.get("players") or []:
        if str(player.get("summonerId", "")) == summoner_id:
            return {"win": bool(player.get("win", False)), "game_length": game_length}, False

    return None, True


def match_result_from_match(match, summoner_id, puuid):
    """Returns (result, identified). identified=False means summoner not found."""
    if match is None:
        return None, False
    game_length = match.get("gameDuration") or 0
    for ident in match.get("participantIdentities") or []:
        player = ident.get("player") or {}
        if not (str(player.get("summonerId", "")) == summoner_id
                or player.get("puuid") == puuid):
            continue
        participant_id = ident.get("participantId")
        for p in match.get("participants") or []:
            if p.get("participantId") == participant_id:
                win = bool((p.get("stats") or {}).get("win", False))
                return {"win": win, "game_length": game_length}, True
    return None, False


def pick_match(games, game_id):
    games = games or []
    for g in games:
        if g.get("gameId") == game_id:
            return g
    if games:
        return games[0]
    return None
