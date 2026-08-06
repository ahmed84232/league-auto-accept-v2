import os
import re
import sys
import zipfile

import requests
from PySide6.QtCore import QThread, Signal


def _version_tuple(version):
    return tuple(int(x) for x in re.findall(r"\d+", version) or [0])


def is_newer(latest, current):
    return _version_tuple(latest) > _version_tuple(current)


class UpdateChecker(QThread):

    # ok, has_update, tag, body, release_url, download_url
    result_signal = Signal(bool, bool, str, str, str, str)

    def __init__(self, owner, repo, current_version, parent=None):
        super().__init__(parent)
        self._owner = owner
        self._repo = repo
        self._current = current_version

    def run(self):
        try:
            url = f"https://api.github.com/repos/{self._owner}/{self._repo}/releases/latest"
            resp = requests.get(
                url, timeout=10, headers={"User-Agent": "league-auto-accept-v2"}
            )
            if resp.status_code != 200:
                self.result_signal.emit(False, False, "", "", "", "")
                return

            data = resp.json()
            tag = data.get("tag_name", "")
            body = data.get("body", "")
            html_url = data.get("html_url", "")
            download_url = ""
            for asset in data.get("assets", []):
                if asset.get("name", "").lower().endswith(".zip"):
                    download_url = asset.get("browser_download_url", "")
                    break
            if not download_url:
                match = re.search(r"https://[^\s)\]]+\.zip", body or "")
                if match:
                    download_url = match.group(0)

            has_update = is_newer(tag, self._current)
            self.result_signal.emit(True, has_update, tag, body, html_url, download_url)
        except requests.RequestException:
            self.result_signal.emit(False, False, "", "", "", "")


class UpdateDownloader(QThread):

    progress_signal = Signal(int)
    done_signal = Signal(bool, str)

    def __init__(self, url, dest_path, parent=None):
        super().__init__(parent)
        self._url = url
        self._dest = dest_path

    def run(self):
        try:
            with requests.get(self._url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(self._dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self.progress_signal.emit(int(downloaded * 100 / total))
            self.done_signal.emit(True, "")
        except requests.RequestException as exc:
            self.done_signal.emit(False, str(exc))


def find_source_root(extracted_dir):
    for dirpath, _, filenames in os.walk(extracted_dir):
        if "main.pyw" in filenames or "main.py" in filenames:
            return dirpath
    return extracted_dir


def extract_update(zip_path, extract_dir):
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)
    return find_source_root(extract_dir)


def pythonw_executable():
    exe = sys.executable
    if "pythonw" in os.path.basename(exe).lower():
        return exe
    candidate = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return candidate if os.path.exists(candidate) else exe


UPDATER_SCRIPT = '''import os
import shutil
import subprocess
import sys
import time


def main():
    app_dir, source_dir, pid, interpreter, launcher = sys.argv[1:6]
    pid = int(pid)
    try:
        import psutil
    except ImportError:
        psutil = None

    if psutil is not None:
        while psutil.pid_exists(pid):
            time.sleep(0.3)
    else:
        time.sleep(3)

    for name in os.listdir(source_dir):
        src = os.path.join(source_dir, name)
        dst = os.path.join(app_dir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    shutil.rmtree(os.path.join(app_dir, ".update"), ignore_errors=True)

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([interpreter, launcher], cwd=app_dir,
                     close_fds=True, creationflags=flags)


if __name__ == "__main__":
    main()
'''
