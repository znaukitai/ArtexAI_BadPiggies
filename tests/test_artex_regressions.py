from unittest.mock import MagicMock, patch
import pytest
from core.input_normalization import normalize_room_query, normalize_api_key
from frontend.gateway import LocalBackend
from mcp_servers.campus_services import find_campus_place


@pytest.mark.parametrize("query", ["C1.226", "где с1.226", "С1 226", "c1-226"])
def test_room_aliases_match_real_records(query):
    result = find_campus_place(query)
    assert result["source"] == "demo"
    assert result["data"]["locations"]
    assert all("226" in loc["code"] and loc["floor"] and loc["block"] for loc in result["data"]["locations"])
    response = LocalBackend(mode="demo").query(query, {"deadlines": []})
    assert "Не понял" not in response.answer
    assert "DEMO" in response.answer
    assert any(step.name == "find_campus_place" for step in response.steps)


def test_missing_room_has_suggestions():
    result = find_campus_place("C1.2.999")
    assert result["data"]["matches_count"] == 0
    assert result["data"]["suggestions"]


def test_key_normalization_and_environment_priority(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "environment-key")
    assert LocalBackend(api_key=' "input-key"\n')._api_key == "input-key"
    assert LocalBackend(api_key="  ")._api_key == "environment-key"
    assert normalize_api_key("\n'key' ") == "key"


def test_connection_requires_success_and_closes_client():
    backend = LocalBackend(api_key="test-key")
    assert "ещё не выполнена" in backend.status
    with patch("google.genai.Client") as client:
        assert backend.check_connection()
        client.return_value.__exit__.assert_called_once()
    assert backend.status.startswith("Gemini подключён")
    with patch("google.genai.Client") as client:
        client.return_value.__enter__.return_value.models.generate_content.side_effect = RuntimeError("403 secret-test-key")
        assert not backend.check_connection()
        client.return_value.__exit__.assert_called_once()
    assert "403" in backend.status and "secret-test-key" not in backend.status


def test_agent_closes_after_setup_failure():
    backend = LocalBackend(api_key="test-key")
    backend.agent = MagicMock()
    backend.agent.query.side_effect = RuntimeError("connection reset test-key")
    with pytest.raises(RuntimeError, match="Gemini не подключён"):
        backend.query("Дедлайны сегодня", {"deadlines": []})
    backend.agent.close.assert_called_once()


def test_normalization_leaves_prose_unchanged():
    assert normalize_room_query("Составь план") == "Составь план"
