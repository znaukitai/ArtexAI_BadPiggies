"""MCP server for GitHub checks and AITU campus search."""

from __future__ import annotations

import json
import difflib
from core.input_normalization import normalize_room_query
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("campus_services")

_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
DEFAULT_GITHUB_REPO = "znaukitai/CampusPulseAI_BadPiggies"

_FACILITY_SYNONYMS: Dict[str, List[str]] = {
    "коворкинг": ["atameken", "coworking", "c1.2", "open space"],
    "coworking": ["atameken", "coworking", "c1.2"],
    "библиотек": ["library", "читальн"],
    "library": ["library"],
    "столов": ["canteen", "асхана", "буфет", "coffee"],
    "canteen": ["canteen", "асхана"],
    "медпункт": ["medical", "мед", "doctor"],
    "деканат": ["registrar", "office", "ssc", "цон"],
    "спорт": ["gym", "sport", "зал"],
    "актов": ["assembly", "hall", "сцена"],
}


def _load_campus_locations() -> List[Dict[str, Any]]:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    map_path = data_dir / "aitu_map_rooms.json"
    demo_path = data_dir / "demo_campus.json"
    places: List[Dict[str, Any]] = []
    try:
        if demo_path.exists():
            demo_payload = json.loads(demo_path.read_text(encoding="utf-8"))
            if isinstance(demo_payload, list):
                places.extend(demo_payload)
            elif isinstance(demo_payload, dict) and isinstance(demo_payload.get("locations"), list):
                places.extend(demo_payload["locations"])
    except (OSError, json.JSONDecodeError):
        pass
    try:
        payload = json.loads(map_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("places"), list):
            places.extend(payload["places"])
    except (OSError, json.JSONDecodeError):
        pass
    return places


def _make_response(
    ok: bool,
    data: Any = None,
    error: Optional[str] = None,
    source: Literal["live", "demo"] = "live",
    start_ns: Optional[int] = None,
) -> Dict[str, Any]:
    elapsed_ms = 0
    if start_ns is not None:
        elapsed_ms = max(0, int((time.perf_counter_ns() - start_ns) / 1_000_000))
    return {
        "ok": ok,
        "data": data,
        "error": error,
        "source": source,
        "elapsed_ms": elapsed_ms,
    }


def validate_and_parse_github_url(repo_url: str) -> Tuple[str, str]:
    """Validate GitHub HTTPS URL or owner/repo shorthand and extract (owner, repo)."""
    if not isinstance(repo_url, str) or not repo_url.strip():
        raise ValueError("repo_url must be a non-empty string.")

    raw = repo_url.strip()
    if "://" not in raw and not raw.startswith("//") and "@" not in raw and ":" not in raw:
        parts = [p for p in raw.strip("/").split("/") if p]
        if len(parts) == 2:
            raw = f"https://github.com/{parts[0]}/{parts[1]}"

    parsed = urlparse(raw)

    if parsed.scheme != "https":
        raise ValueError("SSRF Protection: Only 'https://' GitHub URLs are permitted.")

    if parsed.username or parsed.password:
        raise ValueError("SSRF Protection: Credentials in URL are forbidden.")

    hostname = (parsed.hostname or "").lower()
    if hostname != "github.com":
        raise ValueError(
            f"SSRF Protection: Untrusted host '{hostname}'. Only 'github.com' is allowed."
        )

    if parsed.port not in (None, 443):
        raise ValueError("SSRF Protection: Non-standard ports are forbidden.")

    if parsed.query or parsed.fragment:
        raise ValueError("SSRF Protection: Query parameters and fragments are forbidden.")

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) != 2:
        raise ValueError(
            "Invalid GitHub repository URL. Expected https://github.com/{owner}/{repo}."
        )

    owner, repo = path_parts[0], path_parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    if owner in (".", "..") or repo in (".", ".."):
        raise ValueError("SSRF Protection: Path traversal segments are forbidden.")

    if not _SAFE_SEGMENT_RE.match(owner) or not _SAFE_SEGMENT_RE.match(repo):
        raise ValueError("Invalid characters in repository owner or name.")

    return owner, repo


def _github_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CampusPulse/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _resolve_repo_url(repo_url: Optional[str]) -> str:
    value = (repo_url or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_GITHUB_REPO).strip()
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        return f"https://github.com/{value}"
    return value


@mcp.tool()
def github_repo_status(repo_url: Optional[str] = None) -> Dict[str, Any]:
    """Fetch repository metadata and latest commits from GitHub."""
    start_ns = time.perf_counter_ns()
    repo_url = _resolve_repo_url(repo_url)
    try:
        owner, repo = validate_and_parse_github_url(repo_url)
    except ValueError as exc:
        return _make_response(
            ok=False,
            data=None,
            error=str(exc),
            source="live",
            start_ns=start_ns,
        )

    base_api = f"https://api.github.com/repos/{owner}/{repo}"
    headers = _github_headers()

    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            repo_resp = client.get(base_api, headers=headers)
            if repo_resp.status_code == 404:
                return _make_response(
                    ok=False,
                    data=None,
                    error=f"Репозиторий '{owner}/{repo}' не найден или является приватным (HTTP 404).",
                    source="live",
                    start_ns=start_ns,
                )
            if repo_resp.status_code in (403, 429):
                return _make_response(
                    ok=False,
                    data=None,
                    error="Превышен лимит запросов к GitHub API или доступ ограничен (HTTP 403/429). Укажите GITHUB_TOKEN или повторите позже.",
                    source="live",
                    start_ns=start_ns,
                )
            repo_resp.raise_for_status()
            repo_json = repo_resp.json()

            commits_resp = client.get(
                f"{base_api}/commits",
                headers=headers,
                params={"per_page": 3},
            )
            recent_commits: List[Dict[str, Any]] = []
            empty_repository = False
            if commits_resp.status_code == 409:
                empty_repository = True
            elif commits_resp.status_code == 200:
                for c in commits_resp.json()[:3]:
                    commit_info = c.get("commit", {})
                    author_info = commit_info.get("author", {})
                    raw_msg = str(commit_info.get("message", "")).splitlines()[0][:160]
                    recent_commits.append(
                        {
                            "sha": str(c.get("sha", ""))[:7],
                            "author": author_info.get("name", "unknown"),
                            "date": author_info.get("date", ""),
                            "message": raw_msg,
                        }
                    )

        data = {
            "full_name": repo_json.get("full_name", f"{owner}/{repo}"),
            "html_url": repo_json.get("html_url", f"https://github.com/{owner}/{repo}"),
            "description": str(repo_json.get("description") or "")[:240],
            "default_branch": repo_json.get("default_branch", "main"),
            "language": repo_json.get("language"),
            "open_issues_count": repo_json.get("open_issues_count", 0),
            "stargazers_count": repo_json.get("stargazers_count", 0),
            "updated_at": repo_json.get("updated_at"),
            "pushed_at": repo_json.get("pushed_at"),
            "recent_commits": recent_commits,
            "empty_repository": empty_repository,
        }
        return _make_response(
            ok=True,
            data=data,
            source="live",
            start_ns=start_ns,
        )
    except httpx.HTTPStatusError as exc:
        return _make_response(
            ok=False,
            data=None,
            error=f"Ошибка GitHub API (HTTP {exc.response.status_code}).",
            source="live",
            start_ns=start_ns,
        )
    except httpx.RequestError as exc:
        return _make_response(
            ok=False,
            data=None,
            error=f"Ошибка сети при обращении к GitHub API: {exc}",
            source="live",
            start_ns=start_ns,
        )


@mcp.tool()
def github_assignment_check(
    repo_url: Optional[str] = None,
    expected_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Verify whether expected files exist in a GitHub repository."""
    start_ns = time.perf_counter_ns()
    repo_url = _resolve_repo_url(repo_url)
    try:
        owner, repo = validate_and_parse_github_url(repo_url)
    except ValueError as exc:
        return _make_response(
            ok=False,
            data=None,
            error=str(exc),
            source="live",
            start_ns=start_ns,
        )

    if not expected_files:
        return _make_response(
            ok=False,
            data=None,
            error="expected_files list must not be empty.",
            source="live",
            start_ns=start_ns,
        )

    headers = _github_headers()
    found_files: List[str] = []
    missing_files: List[str] = []

    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            for file_path in expected_files:
                clean_path = file_path.strip().lstrip("/")
                if not clean_path or ".." in clean_path.split("/"):
                    missing_files.append(file_path)
                    continue

                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{clean_path}"
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    found_files.append(clean_path)
                elif resp.status_code == 404:
                    missing_files.append(clean_path)
                else:
                    resp.raise_for_status()

        total = len(expected_files)
        completeness = round((len(found_files) / total) * 100, 1) if total else 0.0

        return _make_response(
            ok=True,
            data={
                "repository": f"{owner}/{repo}",
                "ready_for_submission": len(missing_files) == 0,
                "completeness_pct": completeness,
                "found_files": found_files,
                "missing_files": missing_files,
            },
            source="live",
            start_ns=start_ns,
        )
    except httpx.HTTPStatusError as exc:
        return _make_response(
            ok=False,
            data=None,
            error=f"GitHub API HTTP error {exc.response.status_code}.",
            source="live",
            start_ns=start_ns,
        )
    except httpx.RequestError as exc:
        return _make_response(
            ok=False,
            data=None,
            error=f"Network error contacting GitHub API: {exc}",
            source="live",
            start_ns=start_ns,
        )


@mcp.tool()
def find_campus_place(query: str) -> Dict[str, Any]:
    """Find a room or facility in AITU blocks C1.1-C1.3."""
    start_ns = time.perf_counter_ns()
    locations = _load_campus_locations()
    q = normalize_room_query(query or "").strip().lower()
    if not q:
        matches = locations[:30]
    else:
        normalized = re.sub(r"[^\w.]+", " ", q, flags=re.UNICODE)
        stop_words = {
            "где", "найди", "найти", "находится", "покажи", "комната", "помещение",
            "аудитория", "корпус", "корпусе", "в", "на", "room", "find", "show", "at", "in", "the"
        }
        terms = [term for term in normalized.split() if term not in stop_words]
        expanded_terms = list(terms)
        for t in terms:
            for key, syns in _FACILITY_SYNONYMS.items():
                if key in t:
                    expanded_terms.extend(syns)

        room_query = re.search(r"c1\.(?:[1-3]\.)?\d{3}[klp]?", q, flags=re.IGNORECASE)
        if room_query:
            target = room_query.group(0).upper()
            base_target = re.sub(r"[KLP]$", "", target)
            if target.count(".") == 1:
                number = target.split(".")[1]
                matches = [loc for loc in locations if re.fullmatch(r"C1\.[1-3]\." + re.escape(number) + r"[KLP]?", loc.get("code", "").upper())]
            elif target != base_target:
                matches = [loc for loc in locations if loc.get("code", "").upper() == target]
            else:
                matches = [
                    loc for loc in locations
                    if loc.get("code", "").upper() == target
                    or re.fullmatch(re.escape(target) + r"[KLP]", loc.get("code", "").upper())
                ]
        else:
            def searchable(loc: Dict[str, Any]) -> str:
                return " ".join([
                    str(loc.get("code", "")),
                    str(loc.get("name", "")),
                    str(loc.get("block", "")),
                    str(loc.get("description", "")),
                    *map(str, loc.get("aliases", [])),
                ]).lower()

            meaningful_terms = [term for term in expanded_terms if not re.fullmatch(r"c1(?:\.[1-3])?", term)]
            if meaningful_terms:
                matches = [loc for loc in locations if any(term in searchable(loc) for term in meaningful_terms)]
            else:
                block_query = next((term.upper() for term in terms if re.fullmatch(r"c1(?:\.[1-3])?", term)), "")
                matches = [loc for loc in locations if block_query in loc.get("block", "").upper()]

    return _make_response(
        ok=True,
        data={
            "query": query,
            "matches_count": len(matches),
            "suggestions": difflib.get_close_matches(q.upper().split()[-1] if q else "", [loc.get("code", "") for loc in locations], n=5) if not matches else [],
            "locations": matches[:30],
            "truncated": len(matches) > 30,
            "map_url": "https://yuujiso.github.io/aitumap/",
        },
        source="demo",
        start_ns=start_ns,
    )
