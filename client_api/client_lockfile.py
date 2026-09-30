"""League client lockfile discovery (no Qt, no network)."""

import base64
import os

import psutil

CLIENT_PROCESS = "LeagueClientUx.exe"


def find_lockfile(client_process=CLIENT_PROCESS):
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if proc.info["name"] == client_process and proc.info["exe"]:
                lockfile = os.path.join(os.path.dirname(proc.info["exe"]), "lockfile")
                if os.path.exists(lockfile):
                    return lockfile
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def read_credentials(lockfile):
    with open(lockfile, "r", encoding="utf-8") as f:
        parts = f.read().strip().split(":")
    return parts[2], base64.b64encode(f"riot:{parts[3]}".encode()).decode()
