"""Agent loop tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from agent.campuspulse_agent import CampusPulseAgent
from agent.models import AgentResponse


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
    agent = CampusPulseAgent(model="gemini-2.5-flash", max_steps=6)
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
    agent = CampusPulseAgent(model="gemini-2.5-flash", max_steps=2)
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

    res = agent.query("Зацикленный запрос")
    validated = AgentResponse.model_validate(res)
    assert validated.steps[-1].type == "error"
    assert "max_steps" in (validated.steps[-1].thought or "")
