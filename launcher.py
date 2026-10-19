"""Standalone launcher for Artex AI (starts Streamlit server and opens browser)."""

from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Static imports for PyInstaller dependency analysis when bundling ArtexAI.exe
if False:  # pragma: no cover
    import dotenv  # noqa: F401
    import fastmcp  # noqa: F401
    import google.genai  # noqa: F401
    import httpx  # noqa: F401
    import mcp.server.fastmcp  # noqa: F401
    import pydantic  # noqa: F401
    import streamlit.runtime.scriptrunner.magic_funcs  # noqa: F401
    import streamlit.web.cli  # noqa: F401
    import tzdata  # noqa: F401

    import agent.artex_agent  # noqa: F401
    import agent.mcp_bridge  # noqa: F401
    import agent.models  # noqa: F401
    import agent.prompts  # noqa: F401
    import core.deadline_logic  # noqa: F401
    import frontend.gateway  # noqa: F401
    import frontend.icons  # noqa: F401
    import frontend.ui_components  # noqa: F401
    import mcp_servers.academic_schedule  # noqa: F401
    import mcp_servers.campus_services  # noqa: F401


def resolve_app_root() -> Path:
    """Return base directory whether running from source or PyInstaller bundle."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent


def find_target_port(preferred: int = 8501) -> int:
    """Return preferred port if free, otherwise find an available local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(port: int, timeout_sec: float = 30.0) -> bool:
    """Poll Streamlit health endpoint until server is ready."""
    url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.35)
    return False


def run_streamlit_worker(app_path: str, port: int) -> int:
    """Run Streamlit CLI in-process when invoked with --worker flag."""
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--runner.magicEnabled=false",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    return int(stcli.main() or 0)


def main() -> int:
    root = resolve_app_root()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    app_file = root / "frontend" / "app.py"
    if not app_file.exists():
        print(f"[Artex AI] Файл приложения не найден: {app_file}", file=sys.stderr)
        return 1

    if "--self-test" in sys.argv:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(app_file)).run(timeout=25)
        if list(at.exception):
            for exc in at.exception:
                print(f"[Artex AI Self-Test Error] {exc.value}", file=sys.stderr)
            return 1
        print("[Artex AI Self-Test] OK: frontend/app.py executed with 0 exceptions.")
        return 0

    if "--worker" in sys.argv:
        idx = sys.argv.index("--worker")
        port_arg = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 8501
        return run_streamlit_worker(str(app_file), port_arg)

    port = find_target_port(8501)
    url = f"http://localhost:{port}"

    print("=" * 60)
    print("  Artex AI — ИИ-помощник студента AITU")
    print(f"  Запуск локального сервера на {url} ...")
    print("  Не закрывайте это окно во время работы приложения.")
    print("  При закрытии окна сервер автоматически остановится.")
    print("=" * 60)

    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--worker", str(port)]
    else:
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_file),
            f"--server.port={port}",
            "--server.address=127.0.0.1",
            "--server.headless=true",
            "--runner.magicEnabled=false",
            "--browser.gatherUsageStats=false",
        ]

    proc = subprocess.Popen(cmd, cwd=str(root))

    def _cleanup() -> None:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    atexit.register(_cleanup)

    def _sig_handler(signum: int, _frame: object) -> None:
        _cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    if wait_for_health(port, timeout_sec=35.0):
        print(f"[Artex AI] Сервер готов. Открываю браузер: {url}")
        webbrowser.open(url)
    else:
        print(f"[Artex AI] Откройте в браузере вручную: {url}")

    try:
        return proc.wait()
    except KeyboardInterrupt:
        _cleanup()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
