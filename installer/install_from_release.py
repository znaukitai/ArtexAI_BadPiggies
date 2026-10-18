"""Installer that downloads the latest CampusPulse release from GitHub Releases and creates shortcuts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

GITHUB_REPO = os.environ.get("CAMPUSPULSE_RELEASE_REPO", "znaukitai/CampusPulseAI_BadPiggies")
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Programs" / "CampusPulse"
    return Path.home() / "CampusPulse"


def create_windows_shortcuts(exe_path: Path) -> None:
    """Create Desktop and Start Menu shortcuts on Windows via PowerShell WScript.Shell."""
    if not sys.platform.startswith("win"):
        return

    desktop = Path.home() / "Desktop" / "CampusPulse.lnk"
    appdata = os.environ.get("APPDATA", "")
    start_menu = (
        Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "CampusPulse.lnk"
        if appdata
        else None
    )

    targets = [desktop]
    if start_menu:
        targets.append(start_menu)

    for lnk in targets:
        ps_script = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{lnk}'); "
            f"$s.TargetPath = '{exe_path}'; "
            f"$s.WorkingDirectory = '{exe_path.parent}'; "
            "$s.Description = 'CampusPulse — ИИ-помощник студента AITU'; "
            "$s.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def download_and_install(install_dir: Path) -> Path:
    print(f"[CampusPulse Setup] Проверка последнего релиза в {GITHUB_REPO} ...")
    req = urllib.request.Request(
        RELEASES_API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "CampusPulse-Installer/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        release_data = json.loads(resp.read().decode("utf-8"))

    assets = release_data.get("assets", [])
    zip_asset = next((a for a in assets if str(a.get("name", "")).endswith(".zip")), None)
    exe_asset = next(
        (
            a
            for a in assets
            if str(a.get("name", "")).lower() == "campuspulse.exe"
        ),
        None,
    )

    install_dir.mkdir(parents=True, exist_ok=True)

    if zip_asset:
        dl_url = zip_asset["browser_download_url"]
        print(f"[CampusPulse Setup] Скачивание архива {zip_asset['name']} ...")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "release.zip"
            urllib.request.urlretrieve(dl_url, str(zip_path))
            print(f"[CampusPulse Setup] Распаковка в {install_dir} ...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(install_dir)
    elif exe_asset:
        dl_url = exe_asset["browser_download_url"]
        print(f"[CampusPulse Setup] Скачивание {exe_asset['name']} ...")
        urllib.request.urlretrieve(dl_url, str(install_dir / "CampusPulse.exe"))
    else:
        raise RuntimeError("В последнем релизе GitHub не найден архив CampusPulse-win64.zip или CampusPulse.exe.")

    exe_path = install_dir / "CampusPulse.exe"
    if not exe_path.exists():
        nested = list(install_dir.rglob("CampusPulse.exe"))
        if nested:
            exe_path = nested[0]

    create_windows_shortcuts(exe_path)
    return exe_path


def main() -> int:
    install_dir = get_install_dir()
    try:
        exe_path = download_and_install(install_dir)
        print(f"[CampusPulse Setup] Установка завершена: {exe_path}")
        print("[CampusPulse Setup] Ярлыки созданы на Рабочем столе и в меню Пуск.")
        if exe_path.exists() and "--no-launch" not in sys.argv:
            subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
        return 0
    except Exception as exc:
        print(f"[CampusPulse Setup] Ошибка установки: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
