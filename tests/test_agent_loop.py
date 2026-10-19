"""Agent loop and unrecognized input tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent.campuspulse_agent import CampusPulseAgent, is_unrecognized_or_offtopic
from agent.models import AgentResponse
from frontend.gateway import Gateway


def _make_mock_response(text: str = "", function_calls: list | None = None) -> SimpleNamespace:
    parts = []
    if text:
        parts.append(SimpleNamespace(text=text, function_call=None))
    if function_calls:
        for fc in function_calls:
            parts.append(SimpleNamespace(text=None, function_call=fc))
    content = SimpleNamespace(role="model", parts=parts)
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(
        candidates=[candidate],
        text=text,
        function_calls=function_calls or [],
    )


def test_agent_reasoning_loop_tool_call_and_final() -> None:
    agent = CampusPulseAgent(model="gemini-3.8-flash", max_steps=6)
    agent._bridge = MagicMock()
    agent._bridge.get_callable_tools.return_value = []
    agent._bridge.export_state_after_query.return_value = {"deadlines": []}
    agent._bridge.call_tool.side_effect = [
        {
            "ok": True,
            "data": {"date": "2026-10-18", "weekday": "Sunday", "timezone": "Asia/Almaty"},
            "error": None,
            "source": "live",
            "elapsed_ms": 2,
        },
        {
            "ok": True,
            "data": {"count": 1, "deadlines": [{"title": "Vertex AI Lab", "days_left": 2}]},
            "error": None,
            "source": "demo",
            "elapsed_ms": 4,
        },
    ]

    mock_client = MagicMock()
    turn_1 = _make_mock_response(
        text="Checking current date first.",
        function_calls=[SimpleNamespace(name="get_today", args={})],
    )
    turn_2 = _make_mock_response(
        text="",
        function_calls=[SimpleNamespace(name="list_deadlines", args={"days_ahead": 7})],
    )
    turn_3 = _make_mock_response(
        text="Сегодня 18 октября 2026 года. Ближайший дедлайн: Vertex AI Lab через 2 дня.",
        function_calls=[],
    )
    mock_client.models.generate_content.side_effect = [turn_1, turn_2, turn_3]

    agent._client = mock_client
    agent._system_instruction = "Test instruction"
    agent._backend_mode = "local"

    raw_result = agent.query(
        user_input="Какие у меня дедлайны на этой неделе?",
        session_id="test-session-01",
    )

    validated = AgentResponse.model_validate(raw_result)
    assert "Vertex AI Lab" in validated.answer
    assert validated.meta["tool_calls"] == 2
    assert validated.meta["session_id"] == "test-session-01"

    step_types = [s.type for s in validated.steps]
    assert step_types == [
        "thought",
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_result",
        "final",
    ]
    assert validated.steps[2].source == "live"
    assert validated.steps[4].source == "demo"


def test_agent_loop_respects_max_steps_guard() -> None:
    agent = CampusPulseAgent(model="gemini-3.8-flash", max_steps=2)
    agent._bridge = MagicMock()
    agent._bridge.get_callable_tools.return_value = []
    agent._bridge.export_state_after_query.return_value = {"deadlines": []}
    agent._bridge.call_tool.return_value = {
        "ok": True,
        "data": {"date": "2026-10-18"},
        "error": None,
        "source": "live",
        "elapsed_ms": 1,
    }

    infinite_tool_turn = _make_mock_response(
        text="",
        function_calls=[SimpleNamespace(name="get_today", args={})],
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = infinite_tool_turn

    agent._client = mock_client
    agent._system_instruction = "Test instruction"
    agent._backend_mode = "local"

    res = agent.query("Какие дедлайны на сегодня?")
    validated = AgentResponse.model_validate(res)
    assert validated.steps[-1].type == "error"
    assert "max_steps" in (validated.steps[-1].thought or "")


@pytest.mark.parametrize(
    "bad_input",
    [
        "аывджадв",
        "   ",
        "?",
        "привет",
        "расскажи анекдот",
        "what is the weather",
        "x" * 5000,
    ],
)
def test_unrecognized_or_offtopic_returns_help_without_tools(bad_input: str) -> None:
    assert is_unrecognized_or_offtopic(bad_input) is True
    gw = Gateway("local", api_key="")
    res = gw.query(bad_input, {"deadlines": []})
    if bad_input == "привет":
        assert "Привет" in res.answer and "Не понял запрос" not in res.answer
        assert "дедлайнами" in res.answer
    else:
        assert "Не понял запрос" in res.answer
    assert res.meta.get("tool_calls", 0) == 0
    assert len(res.steps) == 0


def test_valid_deadline_query_triggers_tools() -> None:
    gw = Gateway("local", api_key="")
    res = gw.query("Что горит на этой неделе и с чего начать?", {"deadlines": []})
    assert "Не понял запрос" not in res.answer
    assert res.meta.get("tool_calls", 0) >= 2
    tool_names = [s.name for s in res.steps if s.type == "tool_call"]
    assert "get_today" in tool_names
    assert "list_deadlines" in tool_names


def test_invalid_api_key_reports_explicit_error_without_silent_fallback() -> None:
    from unittest.mock import patch

    with patch("agent.campuspulse_agent.CampusPulseAgent") as patched_cls:
        instance = patched_cls.return_value
        instance.query.return_value = {
            "answer": "Неверный ключ Gemini API или доступ запрещён (HTTP 401/403).",
            "steps": [
                {
                    "index": 0,
                    "type": "error",
                    "thought": "401 API_KEY_INVALID",
                    "source": "live",
                    "started_at": "2026-10-18T12:00:00+05:00",
                    "duration_ms": 12,
                }
            ],
            "state": {"deadlines": []},
            "meta": {
                "model": "gemini-3.8-flash",
                "backend": "error",
                "tool_calls": 0,
                "session_id": "s1",
            },
        }
        gw = Gateway("local", api_key="invalid-key-123")
        res = gw.query("Какие дедлайны на сегодня?", {"deadlines": []})
        assert "Неверный ключ Gemini API" in res.answer
        assert gw.backend.mode_kind == "error"
        assert "Ошибка" in gw.backend.status
        assert res.meta.get("backend") == "error"




