"""Build ArtexAI.exe and ArtexAI_Setup.exe using PyInstaller."""

from __future__ import annotations

import shutil
import hashlib
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
        "--name=ArtexAI",
        "--onedir",
        "--console",
        "--icon=assets/artex-ai.ico",
        f"--add-data=assets{sep}assets",
        f"--add-data=frontend{sep}frontend",
        f"--add-data=agent{sep}agent",
        f"--add-data=core{sep}core",
        f"--add-data=mcp_servers{sep}mcp_servers",
        f"--add-data=data{sep}data",
        f"--add-data=.streamlit/config.toml{sep}.streamlit",
        "--collect-all=streamlit",
        "--collect-all=mcp",
        "--collect-all=fastmcp",
        "--collect-all=google.genai",
        "--collect-all=pydantic",
        "--collect-all=httpx",
        "--collect-all=dotenv",
        "--collect-all=tzdata",
        "--hidden-import=streamlit.runtime.scriptrunner.magic_funcs",
        "--hidden-import=streamlit.web.cli",
        "--hidden-import=mcp.server.fastmcp",
        "--hidden-import=google.genai",
        "--hidden-import=dotenv",
        "--hidden-import=httpx",
        str(ROOT / "launcher.py"),
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    dist_dir = ROOT / "dist" / "ArtexAI"
    if dist_dir.exists():
        archive_base = ROOT / "dist" / "ArtexAI-win64"
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
        "--icon=assets/artex-ai.ico",
        "--name=ArtexAI_Setup",
        str(installer_script),
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)


if __name__ == "__main__":
    build_launcher_exe()
    build_web_installer_exe()
    assets = [ROOT / "dist" / name for name in ("ArtexAI-win64.zip", "ArtexAI_Setup.exe")]
    checksums = []
    for asset in assets:
        with asset.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        checksums.append(f"{digest}  {asset.name}")
    (ROOT / "dist" / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
