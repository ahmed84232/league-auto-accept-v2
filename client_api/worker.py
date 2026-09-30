import os
import time
import urllib3

import requests
from PySide6.QtCore import QThread, Signal

from client_api import league_api
from client_api import client_lockfile
from game_rules import accept_rules
from game_rules import result_text
from game_rules import rank_math

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LpBackfillWorker(QThread):

    correction_signal = Signal(dict)
    log_signal = Signal(str, str)

    BACKFILL_TRIES = 17
    BACKFILL_INTERVAL = 10.0

    def __init__(self, port, auth_token, pre, game_id, parent=None):
        super().__init__(parent)
        self._port = port
        self._auth_token = auth_token
        self._pre = dict(pre) if pre else None
        self._game_id = game_id
        self._running = True

    def stop(self):
        self._running = False

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while self._running and time.monotonic() < end:
            time.sleep(0.5)

    def _ranked_stats(self, session, base):
        try:
            resp = session.get(
                f"{base}/lol-ranked/v1/current-ranked-stats", timeout=5
            )
        except requests.RequestException:
            return None
        if resp.status_code == 404:
            return None
        try:
            data = resp.json()
        except ValueError:
            return None
        if not data:
            return None
        entry = league_api.ranked_entry_from_data(data, rank_math.RANKED_QUEUE_NAME)
        if not entry:
            return None
        return league_api.normalize_ranked_entry(entry)

    def run(self):
        if not self._running or self._pre is None:
            return
        session = league_api.build_session(self._auth_token)
        base = league_api.base_url(self._port)
        try:
            for _ in range(self.BACKFILL_TRIES):
                if not self._running:
                    return
                post = self._ranked_stats(session, base)
                if post is not None and AutoAcceptWorker._stats_changed(
                    self._pre, post
                ):
                    delta = AutoAcceptWorker._lp_delta(self._pre, post)
                    self.log_signal.emit(
                        f"LP update arrived late  ({delta:+d} LP)"
                        if delta is not None
                        else "LP update arrived late",
                        "success",
                    )
                    self.correction_signal.emit({
                        "correction": True,
                        "game_id": self._game_id,
                        "lp_delta": delta,
                        "post": post,
                    })
                    return
                self._sleep(self.BACKFILL_INTERVAL)
            self.log_signal.emit(
                "LP change not observed — showing — (will retry next game)",
                "warning",
            )
        finally:
            session.close()


class AutoAcceptWorker(QThread):

    log_signal = Signal(str, str)
    phase_signal = Signal(str)
    connected_signal = Signal(bool)
    match_accepted_signal = Signal()
    game_started_signal = Signal()
    game_result_signal = Signal(dict)
    game_result_correction_signal = Signal(dict)

    CLIENT_PROCESS = client_lockfile.CLIENT_PROCESS
    RANKED_QUEUE_ID = rank_math.RANKED_QUEUE_ID
    RANKED_QUEUE_NAME = rank_math.RANKED_QUEUE_NAME

    TIERS = rank_math.TIERS
    DIVISIONS = rank_math.DIVISIONS

    GAME_ACTIVE_PHASES = accept_rules.GAME_ACTIVE_PHASES
    READY_CHECK_COOLDOWN = accept_rules.READY_CHECK_COOLDOWN

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._lockfile = None
        self._last_log = None
        self._ranked_game = None
        self._midgame_checked = False
        self._last_accept_ts = 0.0
        self._backfills = []

    def _should_accept(self, data):
        return accept_rules.should_accept(
            data, self._last_accept_ts, time.monotonic(), self.READY_CHECK_COOLDOWN
        )

    def stop(self):
        self._running = False
        for worker in list(self._backfills):
            worker.stop()

    def find_lockfile(self):
        cached = self._lockfile
        if cached and os.path.exists(cached):
            return cached

        found = client_lockfile.find_lockfile(self.CLIENT_PROCESS)
        self._lockfile = found
        return found

    @staticmethod
    def read_credentials(client_lockfile_path):
        return client_lockfile.read_credentials(client_lockfile_path)

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
        return league_api.queue_id_from_session(data)

    def _session_context(self, session, base):
        data = self._get(session, f"{base}/lol-gameflow/v1/session", "gameflow/session")
        return league_api.session_context_from_session(data)

    def _current_summoner_id(self, session, base):
        data = self._get(session, f"{base}/lol-summoner/v1/current-summoner", "summoner/current-summoner")
        return league_api.summoner_id_from_summoner(data)

    def _ranked_stats(self, session, base):
        data = self._get(
            session,
            f"{base}/lol-ranked/v1/current-ranked-stats",
            "ranked/current-ranked-stats",
        )
        entry = league_api.ranked_entry_from_data(data, self.RANKED_QUEUE_NAME)
        if not entry:
            if data:
                self._log(
                    f"current-ranked-stats: no entry for {self.RANKED_QUEUE_NAME} "
                    f"(unranked or missing). Keys: {league_api.queue_keys(data)}",
                    "info",
                )
            return None
        return league_api.normalize_ranked_entry(entry)

    @staticmethod
    def _stats_changed(a, b):
        return rank_math.stats_changed(a, b)

    @classmethod
    def _rank_points(cls, stats):
        return rank_math.rank_points(stats)

    @classmethod
    def _lp_delta(cls, pre, post):
        return rank_math.lp_delta(pre, post)

    def _wait_for_ranked_update(self, session, base, pre, tries=8, interval=2.0):
        post = None
        for _ in range(tries):
            post = self._ranked_stats(session, base)
            if post is not None and (pre is None or self._stats_changed(pre, post)):
                return post
            self._sleep(interval)
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
        result, undetermined = league_api.eog_result_from_data(data, summoner_id)
        if result is not None:
            return result

        local = data.get("localPlayer") or {}
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
            match = league_api.pick_match(games, game_id)
            if match is None:
                self._sleep(1)
                continue

            result, identified = league_api.match_result_from_match(match, summoner_id, puuid)
            if result is not None:
                return result
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

    def _cleanup_backfills(self):
        self._backfills = [w for w in self._backfills if w.isRunning()]

    def _spawn_backfill(self, session, base, pre, game_id):
        try:
            port = base.rsplit(":", 1)[-1]
            auth_header = session.headers.get("Authorization", "")
            token = auth_header[6:].strip() if auth_header.startswith("Basic ") else ""
        except (AttributeError, IndexError):
            return
        if not port or pre is None:
            return
        self._cleanup_backfills()
        backfill = LpBackfillWorker(port, token, pre, game_id)
        backfill.correction_signal.connect(self.game_result_correction_signal.emit)
        backfill.log_signal.connect(self._forward_backfill_log)
        backfill.finished.connect(lambda: self._cleanup_backfills())
        self._backfills.append(backfill)
        self._log("LP not updated yet — will backfill when client catches up", "info")
        backfill.start()

    def _forward_backfill_log(self, message, level):
        self._log(message, level)

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

        decision = result_text.decide_result_text(pre, post, eog, game_id)
        pending = decision["pending"]
        remake = decision["remake"]

        self._log(decision["text"], decision["level"])
        self.game_result_signal.emit(decision["payload"])

        if pending and not remake and self._running:
            self._spawn_backfill(session, base, pre, game_id)

    def run(self):
        if not self._running:
            return

        session = league_api.build_session()

        try:
            while self._running:
                client_lockfile_path = self.find_lockfile()
                if not client_lockfile_path:
                    self._log("League client is off.", "warning")
                    self.connected_signal.emit(False)
                    self.phase_signal.emit("Searching...")
                    self._sleep(3)
                    continue

                try:
                    port, auth = self.read_credentials(client_lockfile_path)
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
        base = league_api.base_url(port)
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

                data = rc.json()
                state = data.get("state")
                if state == "Invalid":
                    self._log("No match found yet", "info")
                    self._sleep(2)
                elif state == "InProgress":
                    if not self._should_accept(data):
                        # Same prompt still open (or answered) — wait it out.
                        self._sleep(3)
                        continue
                    self._log("Match Found", "success")
                    try:
                        resp = session.post(accept, timeout=5)
                        ok = resp.status_code < 400
                    except requests.RequestException:
                        ok = False
                    if ok:
                        self._last_accept_ts = time.monotonic()
                        self._log("Match accepted! Waiting for players...", "success")
                        self.match_accepted_signal.emit()
                    else:
                        self._log("Accept failed, will retry...", "warning")
                    # The client prompt lives ~10s either way; wait it out
                    # instead of hammering accept.
                    self._sleep(10)
                elif state == "Searching":
                    self._sleep(2)
                else:
                    self._log("Waiting for you to press Find Match...", "info")
                    self._sleep(5)
            except (requests.RequestException, ValueError) as exc:
                self._log(f"Connection error: {exc}", "error")
                return
