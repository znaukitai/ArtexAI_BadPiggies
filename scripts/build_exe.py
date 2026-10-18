"""Build CampusPulse.exe and CampusPulse_Setup.exe using PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_launcher_exe() -> None:
    sep = ";" if sys.platform.startswith("win") else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name=CampusPulse",
        "--onedir",
        "--console",
        f"--add-data=frontend{sep}frontend",
        f"--add-data=agent{sep}agent",
        f"--add-data=core{sep}core",
        f"--add-data=mcp_servers{sep}mcp_servers",
        f"--add-data=data{sep}data",
        f"--add-data=.streamlit{sep}.streamlit",
        "--copy-metadata=streamlit",
        "--copy-metadata=google-genai",
        "--copy-metadata=mcp",
        "--copy-metadata=pydantic",
        "--collect-data=streamlit",
        "--hidden-import=streamlit.web.cli",
        "--hidden-import=mcp.server.fastmcp",
        "--hidden-import=google.genai",
        str(ROOT / "launcher.py"),
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    dist_dir = ROOT / "dist" / "CampusPulse"
    if dist_dir.exists():
        archive_base = ROOT / "dist" / "CampusPulse-win64"
        shutil.make_archive(str(archive_base), "zip", root_dir=str(dist_dir))


def build_web_installer_exe() -> None:
    installer_script = ROOT / "installer" / "install_from_release.py"
    if not installer_script.exists():
        return
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name=CampusPulse_Setup",
        str(installer_script),
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)


if __name__ == "__main__":
    build_launcher_exe()
    build_web_installer_exe()
