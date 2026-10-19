"""MCP tools tests."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mcp_servers.academic_schedule import (
    add_deadline,
    get_today,
    list_deadlines,
    parse_syllabus_text,
    plan_week,
    reset_deadline_store,
)
from mcp_servers.campus_services import (
    find_campus_place,
    github_assignment_check,
    github_repo_status,
    validate_and_parse_github_url,
)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    reset_deadline_store()


def test_get_today_envelope() -> None:
    res = get_today()
    assert res["ok"] is True
    assert res["source"] == "live"
    assert "date" in res["data"]
    assert res["data"]["timezone"] == "Asia/Almaty"


def test_add_and_list_deadline() -> None:
    from datetime import timedelta
    from mcp_servers.academic_schedule import _now_almaty

    due = (_now_almaty().date() + timedelta(days=3)).isoformat()
    res_add = add_deadline(
        course="CS405 Cloud Computing",
        title="Vertex AI Deployment Lab",
        due_date=due,
        priority="critical",
    )
    assert res_add["ok"] is True
    assert res_add["data"]["added"]["course"] == "CS405 Cloud Computing"
    assert res_add["data"]["added"]["source"] == "live"

    res_list = list_deadlines(days_ahead=60, course="CS405")
    assert res_list["ok"] is True
    assert res_list["data"]["count"] == 1
    assert res_list["data"]["deadlines"][0]["priority"] == "critical"
    assert res_list["data"]["deadlines"][0]["source"] == "live"


def test_default_demo_deadlines_relative_to_fixed_date_2026_10_30() -> None:
    from datetime import date, datetime, timezone, timedelta

    fixed_now = datetime(2026, 10, 30, 10, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    with patch("mcp_servers.academic_schedule._now_almaty", return_value=fixed_now):
        reset_deadline_store(reference_date=date(2026, 10, 30))
        res_list = list_deadlines(days_ahead=30)
        assert res_list["ok"] is True
        items = res_list["data"]["deadlines"]
        assert len(items) == 3
        for item in items:
            assert item["days_left"] >= 0
            assert item["urgency"] != "overdue"
            assert item["source"] == "demo"


def test_add_deadline_rejects_bad_date() -> None:
    res = add_deadline(
        course="CS101",
        title="Bad Date",
        due_date="21/10/2026",
        priority="low",
    )
    assert res["ok"] is False
    assert "Invalid ISO 8601" in (res["error"] or "")


def test_plan_week_and_parse_syllabus() -> None:
    plan_res = plan_week(start_date="2026-10-18")
    assert plan_res["ok"] is True
    assert len(plan_res["data"]["days"]) == 7

    parsed_res = parse_syllabus_text("SE202 - Capstone Milestone 1 due 2026-10-28 [high]")
    assert parsed_res["ok"] is True
    assert parsed_res["data"]["saved"] is False
    assert parsed_res["data"]["candidates_count"] == 1


def test_ssrf_protection_blocks_malicious_urls() -> None:
    with pytest.raises(ValueError, match="Only 'https://'"):
        validate_and_parse_github_url("http://github.com/owner/repo")

    with pytest.raises(ValueError, match="Untrusted host"):
        validate_and_parse_github_url("https://169.254.169.254/latest/meta-data")

    with pytest.raises(ValueError, match="Untrusted host"):
        validate_and_parse_github_url("https://localhost/admin/config")

    with pytest.raises(ValueError, match="Credentials in URL"):
        validate_and_parse_github_url("https://user:pass@github.com/owner/repo")

    owner, repo = validate_and_parse_github_url("https://github.com/google/genai-sdk.git")
    assert owner == "google"
    assert repo == "genai-sdk"


@patch("mcp_servers.campus_services.httpx.Client")
def test_github_repo_status_mocked(mock_client_cls: Any) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client

    repo_response = MagicMock()
    repo_response.status_code = 200
    repo_response.json.return_value = {
        "full_name": "znaukitai/CampusPulseAI_BadPiggies",
        "html_url": "https://github.com/znaukitai/CampusPulseAI_BadPiggies",
        "description": "Student assistant",
        "default_branch": "main",
        "language": "Python",
        "open_issues_count": 2,
        "stargazers_count": 15,
        "updated_at": "2026-10-18T08:00:00Z",
        "pushed_at": "2026-10-18T08:05:00Z",
    }

    commits_response = MagicMock()
    commits_response.status_code = 200
    commits_response.json.return_value = [
        {
            "sha": "a1b2c3d4e5f6",
            "commit": {
                "author": {"name": "Dev", "date": "2026-10-18T08:05:00Z"},
                "message": "feat: add MCP bridge",
            },
        }
    ]

    mock_client.get.side_effect = [repo_response, commits_response]

    res = github_repo_status("https://github.com/znaukitai/CampusPulseAI_BadPiggies")
    assert res["ok"] is True
    assert res["source"] == "live"
    assert res["data"]["full_name"] == "znaukitai/CampusPulseAI_BadPiggies"
    assert len(res["data"]["recent_commits"]) == 1
    assert res["data"]["recent_commits"][0]["sha"] == "a1b2c3d"


@patch("mcp_servers.campus_services.httpx.Client")
def test_github_assignment_check_mocked(mock_client_cls: Any) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client

    found_resp = MagicMock(status_code=200)
    missing_resp = MagicMock(status_code=404)
    mock_client.get.side_effect = [found_resp, missing_resp]

    res = github_assignment_check(
        "https://github.com/znaukitai/CampusPulseAI_BadPiggies",
        ["README.md", "deployment/deploy.py"],
    )
    assert res["ok"] is True
    assert res["source"] == "live"
    assert res["data"]["ready_for_submission"] is False
    assert res["data"]["completeness_pct"] == 50.0
    assert res["data"]["found_files"] == ["README.md"]
    assert res["data"]["missing_files"] == ["deployment/deploy.py"]


def test_find_campus_place_aitu() -> None:
    res = find_campus_place("Где находится C1.2.223?")
    assert res["ok"] is True
    assert res["source"] == "demo"
    assert res["data"]["matches_count"] >= 1
    assert res["data"]["locations"][0]["code"].startswith("C1.2.223")
    assert res["data"]["locations"][0]["floor"] == 2


def test_github_url_shorthand_and_query_blocking() -> None:
    owner, repo = validate_and_parse_github_url("znaukitai/CampusPulseAI_BadPiggies")
    assert owner == "znaukitai"
    assert repo == "CampusPulseAI_BadPiggies"

    with pytest.raises(ValueError, match="Query parameters"):
        validate_and_parse_github_url("https://github.com/owner/repo?tab=readme")

    with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
        validate_and_parse_github_url("https://github.com/owner/repo/extra/segment")


@patch("mcp_servers.campus_services.httpx.Client")
def test_github_repo_status_error_codes_and_empty_repo(mock_client_cls: Any) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client

    mock_client.get.return_value = MagicMock(status_code=404)
    res_404 = github_repo_status("znaukitai/nonexistent-repo")
    assert res_404["ok"] is False
    assert "404" in (res_404["error"] or "")

    mock_client.get.return_value = MagicMock(status_code=403)
    res_403 = github_repo_status("znaukitai/rate-limited")
    assert res_403["ok"] is False
    assert "403" in (res_403["error"] or "")

    repo_ok = MagicMock(status_code=200)
    repo_ok.json.return_value = {
        "full_name": "znaukitai/empty-repo",
        "html_url": "https://github.com/znaukitai/empty-repo",
        "default_branch": "main",
    }
    commits_409 = MagicMock(status_code=409)
    mock_client.get.side_effect = [repo_ok, commits_409]
    res_empty = github_repo_status("znaukitai/empty-repo")
    assert res_empty["ok"] is True
    assert res_empty["data"]["empty_repository"] is True
    assert res_empty["data"]["recent_commits"] == []


def test_html_escaping() -> None:
    import html

    xss_title = "<script>alert('xss')</script>"
    escaped = html.escape(xss_title)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_launcher_port_and_root() -> None:
    from launcher import find_target_port, resolve_app_root

    root = resolve_app_root()
    assert (root / "frontend" / "app.py").exists()
    port = find_target_port(8599)
    assert isinstance(port, int) and port > 1024


