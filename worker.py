import base64
import os
import time
import urllib3

import psutil
import requests
from PySide6.QtCore import QThread, Signal

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AutoAcceptWorker(QThread):

    log_signal = Signal(str, str)
    phase_signal = Signal(str)
    connected_signal = Signal(bool)
    match_accepted_signal = Signal()
    game_started_signal = Signal()
    game_result_signal = Signal(dict)

    CLIENT_PROCESS = "LeagueClientUx.exe"
    RANKED_QUEUE_ID = 420
    RANKED_QUEUE_NAME = "RANKED_SOLO_5x5"

    TIERS = (
        "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD",
        "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER",
    )
    DIVISIONS = ("IV", "III", "II", "I")

    GAME_ACTIVE_PHASES = ("ChampSelect", "GameStart", "InProgress", "InGame", "Reconnect")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._lockfile = None
        self._last_log = None
        self._ranked_game = None
        self._midgame_checked = False

    def stop(self):
        self._running = False

    def find_lockfile(self):
        cached = self._lockfile
        if cached and os.path.exists(cached):
            return cached

        for proc in psutil.process_iter(["name", "exe"]):
            try:
                if proc.info["name"] == self.CLIENT_PROCESS and proc.info["exe"]:
                    lockfile = os.path.join(os.path.dirname(proc.info["exe"]), "lockfile")
                    if os.path.exists(lockfile):
                        self._lockfile = lockfile
                        return lockfile
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        self._lockfile = None
        return None

    @staticmethod
    def read_credentials(lockfile):
        with open(lockfile, "r", encoding="utf-8") as f:
            parts = f.read().strip().split(":")
        return parts[2], base64.b64encode(f"riot:{parts[3]}".encode()).decode()

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while self._running and time.monotonic() < end:
            time.sleep(0.2)

    def _log(self, message, level="info"):
        if (message, level) != self._last_log:
            self._last_log = (message, level)
            self.log_signal.emit(message, level)

    def _get(self, session, url, log_label=None):
        resp = session.get(url, timeout=5)
        if resp.status_code == 404:
            if log_label:
                self._log(f"{log_label}: HTTP 404 (endpoint or data not available)", "warning")
            return None
        return resp.json()

    def _queue_id(self, session, base):
        data = self._get(session, f"{base}/lol-gameflow/v1/session", "gameflow/session")
        if not data:
            return None
        game_data = data.get("gameData") or {}
        queue_id = game_data.get("queueId")
        if queue_id is None:
            queue_id = (game_data.get("queue") or {}).get("id")
        return queue_id

    def _session_context(self, session, base):
        data = self._get(session, f"{base}/lol-gameflow/v1/session", "gameflow/session")
        if not data:
            return None, None
        game_data = data.get("gameData") or {}
        queue_id = game_data.get("queueId")
        if queue_id is None:
            queue_id = (game_data.get("queue") or {}).get("id")
        return queue_id, game_data.get("gameId")

    def _current_summoner_id(self, session, base):
        data = self._get(session, f"{base}/lol-summoner/v1/current-summoner", "summoner/current-summoner")
        if not data:
            return None
        return str(data.get("summonerId", ""))

    def _ranked_stats(self, session, base):
        data = self._get(
            session,
            f"{base}/lol-ranked/v1/current-ranked-stats",
            "ranked/current-ranked-stats",
        )
        if not data:
            return None
        entry = (data.get("queueMap") or {}).get(self.RANKED_QUEUE_NAME)
        if not entry:
            entry = data.get("highestRankedEntrySR") or data.get("highestRankedEntry")
        if not entry:
            self._log(
                f"current-ranked-stats: no entry for {self.RANKED_QUEUE_NAME} "
                f"(unranked or missing). Keys: {list((data.get('queueMap') or {}).keys())}",
                "info",
            )
            return None
        return {
            "tier": entry.get("tier"),
            "division": entry.get("division"),
            "lp": entry.get("leaguePoints"),
            "wins": entry.get("wins"),
            "losses": entry.get("losses"),
        }

    @staticmethod
    def _stats_changed(a, b):
        return any(a.get(k) != b.get(k) for k in ("tier", "division", "lp", "wins", "losses"))

    @classmethod
    def _rank_points(cls, stats):
        tier = (stats or {}).get("tier")
        division = (stats or {}).get("division")
        lp = (stats or {}).get("lp") or 0
        if tier not in cls.TIERS or division not in cls.DIVISIONS:
            return None
        return cls.TIERS.index(tier) * 400 + cls.DIVISIONS.index(division) * 100 + lp

    @classmethod
    def _lp_delta(cls, pre, post):
        if pre is None or post is None:
            return None
        pre_pts = cls._rank_points(pre)
        post_pts = cls._rank_points(post)
        if pre_pts is None or post_pts is None:
            return None
        return post_pts - pre_pts

    def _wait_for_ranked_update(self, session, base, pre):
        post = None
        for _ in range(8):
            post = self._ranked_stats(session, base)
            if post is not None and (pre is None or self._stats_changed(pre, post)):
                return post
            self._sleep(1)
        return post

    def _fetch_eog_result(self, session, base, summoner_id):
        data = None
        for _ in range(8):
            data = self._get(session, f"{base}/lol-end-of-game/v1/eog-stats-block", "eog-stats-block")
            if data is not None:
                break
            self._sleep(1)
        if data is None:
            return None
        game_length = (
            data.get("gameLength")
            or (data.get("gameData") or {}).get("gameLength")
            or 0
        )

        local = data.get("localPlayer") or {}
        local_stats = local.get("stats") or {}
        if local_stats.get("WIN") == 1:
            return {"win": True, "game_length": game_length}
        if local_stats.get("LOSE") == 1:
            return {"win": False, "game_length": game_length}

        for team in data.get("teams") or []:
            if team.get("isPlayerTeam"):
                return {"win": bool(team.get("isWinningTeam")), "game_length": game_length}

        for player in data.get("players") or []:
            if str(player.get("summonerId", "")) == summoner_id:
                return {"win": bool(player.get("win", False)), "game_length": game_length}

        self._log(
            "eog-stats-block: could not determine result "
            f"(localPlayer keys: {list(local.keys())}, teams: {len(data.get('teams') or [])})",
            "warning",
        )
        return None

    def _fetch_result_from_match_history(self, session, base, game_id, summoner_id, puuid):
        for _ in range(8):
            data = self._get(
                session,
                f"{base}/lol-match-history/v1/products/lol/{puuid}/matches",
                "match-history/matches",
            )
            if data is None:
                self._sleep(1)
                continue
            games = ((data.get("games") or {}).get("games")) or []
            match = None
            for g in games:
                if g.get("gameId") == game_id:
                    match = g
                    break
            if match is None and games:
                match = games[0]
            if match is None:
                self._sleep(1)
                continue

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
                        return {"win": win, "game_length": game_length}
            self._log("match-history: could not identify summoner in match", "warning")
            self._sleep(1)
        return None

    def _begin_ranked_tracking(self, session, base):
        queue_id, game_id = self._session_context(session, base)
        if queue_id != self.RANKED_QUEUE_ID:
            return None
        summoner = self._get(
            session, f"{base}/lol-summoner/v1/current-summoner", "summoner/current-summoner"
        ) or {}
        pre = self._ranked_stats(session, base)
        self._log("Ranked Solo/Duo game detected — tracking session stats", "info")
        return {
            "pre": pre,
            "summoner_id": str(summoner.get("summonerId", "")),
            "puuid": summoner.get("puuid", ""),
            "game_id": game_id,
            "started": False,
        }

    def _begin_midgame_tracking(self, session, base):
        queue_id, game_id = self._session_context(session, base)
        if queue_id != self.RANKED_QUEUE_ID:
            return None
        summoner = self._get(
            session, f"{base}/lol-summoner/v1/current-summoner", "summoner/current-summoner"
        ) or {}
        self._log("Ranked Solo/Duo game already in progress — tracking result", "info")
        return {
            "pre": None,
            "summoner_id": str(summoner.get("summonerId", "")),
            "puuid": summoner.get("puuid", ""),
            "game_id": game_id,
            "started": True,
        }

    def _finalize_ranked_game(self, session, base):
        game = self._ranked_game
        self._ranked_game = None
        if game is None:
            return
        if not game.get("started"):
            self._log("Champion select ended — no game started", "info")
            return

        pre = game.get("pre")
        summoner_id = game.get("summoner_id")
        puuid = game.get("puuid", "")
        game_id = game.get("game_id")
        eog = self._fetch_eog_result(session, base, summoner_id)
        if eog is None:
            self._log("eog-stats-block unavailable, falling back to match history", "info")
            eog = self._fetch_result_from_match_history(
                session, base, game_id, summoner_id, puuid
            )
        post = self._wait_for_ranked_update(session, base, pre)

        remake = bool(eog and (eog.get("game_length") or 0) < 300)
        win = None if remake else (eog.get("win") if eog else None)

        lp_delta = self._lp_delta(pre, post)

        if remake:
            text = "Game over — remake, result not counted"
        elif win is True:
            text = "Victory!"
            if lp_delta is not None:
                text += f"  ({lp_delta:+d} LP)"
        elif win is False:
            text = "Defeat"
            if lp_delta is not None:
                text += f"  ({lp_delta:+d} LP)"
        else:
            text = "Game over — result unknown"

        self._log(text, "success" if win else "warning")
        self.game_result_signal.emit({
            "result": "win" if win is True else "loss" if win is False else "unknown",
            "remake": remake,
            "lp_delta": lp_delta,
            "post": post,
        })

    def run(self):
        if not self._running:
            return

        session = requests.Session()
        session.verify = False
        session.headers["Accept"] = "application/json"

        try:
            while self._running:
                lockfile = self.find_lockfile()
                if not lockfile:
                    self._log("LeagueClientUx.exe process not found.", "warning")
                    self.connected_signal.emit(False)
                    self.phase_signal.emit("Searching...")
                    self._sleep(3)
                    continue

                try:
                    port, auth = self.read_credentials(lockfile)
                except (IndexError, OSError) as exc:
                    self._log(f"Failed to read lockfile: {exc}", "error")
                    self.connected_signal.emit(False)
                    self._sleep(3)
                    continue

                session.headers["Authorization"] = f"Basic {auth}"
                self._log(f"Connected to client (port {port})", "success")
                self.connected_signal.emit(True)

                self._poll(session, port)

                if not self._running:
                    break

                self._log("Lost connection, reconnecting...", "warning")
                self.connected_signal.emit(False)
                self._sleep(3)
        finally:
            session.close()
            self.connected_signal.emit(False)
            self.phase_signal.emit("Stopped")

    def _poll(self, session, port):
        base = f"https://127.0.0.1:{port}"
        phase_url = f"{base}/lol-gameflow/v1/gameflow-phase"
        ready_check = f"{base}/lol-matchmaking/v1/ready-check"
        accept = f"{base}/lol-matchmaking/v1/ready-check/accept"

        while self._running:
            try:
                phase_resp = session.get(phase_url, timeout=5)
                phase = None if phase_resp.status_code == 404 else phase_resp.json()
                self.phase_signal.emit(phase or "None")

                if phase in self.GAME_ACTIVE_PHASES:
                    if phase in ("InProgress", "InGame"):
                        if self._ranked_game is None and not self._midgame_checked:
                            self._midgame_checked = True
                            game = self._begin_midgame_tracking(session, base)
                            if game is not None:
                                self._ranked_game = game
                                self.game_started_signal.emit()
                        elif self._ranked_game is not None and not self._ranked_game.get("started"):
                            self._ranked_game["started"] = True
                            self.game_started_signal.emit()
                        self._log("Game in progress...", "info")
                        self._sleep(10)
                    else:
                        if phase == "ChampSelect" and self._ranked_game is None and not self._midgame_checked:
                            self._midgame_checked = True
                            game = self._begin_ranked_tracking(session, base)
                            if game is not None:
                                self._ranked_game = game
                        self._sleep(5 if phase == "ChampSelect" else 3)
                    continue

                self._midgame_checked = False
                if self._ranked_game is not None:
                    self._finalize_ranked_game(session, base)
                    self._sleep(3)
                    continue

                rc = session.get(ready_check, timeout=5)
                if rc.status_code == 404:
                    self._log("Waiting for you to press Find Match...", "info")
                    self._sleep(3)
                    continue

                state = rc.json().get("state")
                if state == "Invalid":
                    self._log("No match found yet", "info")
                    self._sleep(2)
                elif state == "InProgress":
                    self._log("Match Found", "success")
                    session.post(accept, timeout=5)
                    self._log("Match accepted!", "success")
                    self.match_accepted_signal.emit()
                    self._sleep(5)
                elif state == "Searching":
                    self._sleep(2)
                else:
                    self._log("Waiting for you to press Find Match...", "info")
                    self._sleep(5)
            except (requests.RequestException, ValueError) as exc:
                self._log(f"Connection error: {exc}", "error")
                return
