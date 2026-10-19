"""Offline integration checks using real GenAI payload models."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from google.genai import errors, types

from agent.artex_agent import ArtexAgent
from agent.mcp_bridge import InMemoryMCPBridge
from frontend.gateway import CloudBackend


def configured_agent() -> ArtexAgent:
    agent = ArtexAgent(api_key="test-key")
    agent._client = MagicMock()
    agent._bridge = InMemoryMCPBridge()
    agent._system_instruction = "Use tools to answer."
    agent._backend_mode = "local"
    return agent


def response(*parts: types.Part) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=list(parts)), finish_reason="STOP",
    )])


def test_explicit_cloud_project_wins_over_environment_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "local-secret")
    with patch("google.genai.Client") as client:
        ArtexAgent(project="cloud-project", model_location="global").set_up()
    assert client.call_args.kwargs["vertexai"] is True
    assert "api_key" not in client.call_args.kwargs
    assert client.call_args.kwargs["location"] == "global"


def test_developer_client_overrides_vertex_environment(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    with patch("google.genai.Client") as client:
        ArtexAgent(api_key="test-key").set_up()
    assert client.call_args.kwargs["vertexai"] is False


def test_cloud_model_selection_is_preserved(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    assert CloudBackend(project="test").model == "gemini-2.5-flash"


def test_setup_failure_returns_state_and_safe_error(caplog):
    agent = ArtexAgent(api_key="secret-key")
    with patch("google.genai.Client", side_effect=ValueError("secret-key")):
        result = agent.query("deadlines today", {"deadlines": [], "custom": 1})
    assert result["steps"][-1]["type"] == "error"
    assert result["state"] == {"deadlines": [], "custom": 1}
    assert "secret-key" not in str(result) + caplog.text


def test_parallel_calls_preserve_signatures_ids_and_order():
    agent = configured_agent()
    model_response = response(
        types.Part(text="private reasoning", thought=True),
        types.Part(function_call=types.FunctionCall(name="get_today", args={}, id="a"),
                   thought_signature=b"signature"),
        types.Part(function_call=types.FunctionCall(name="list_deadlines", args={}, id="b")),
    )
    snapshots = []

    def generate(**kwargs):
        snapshots.append(list(kwargs["contents"]))
        return model_response if len(snapshots) == 1 else response(types.Part(text="Done"))

    agent._client.models.generate_content.side_effect = generate
    result = agent.query("deadlines today", {"deadlines": []})
    assert result["answer"] == "Done"
    assert result["meta"]["tool_calls"] == 2
    assert snapshots[1][1] is model_response.candidates[0].content
    assert snapshots[1][1].parts[1].thought_signature == b"signature"
    assert [p.function_response.id for p in snapshots[1][2].parts] == ["a", "b"]
    assert "private reasoning" not in str(result)


@pytest.mark.parametrize("model_response", [
    types.GenerateContentResponse(),
    response(types.Part(text="private", thought=True)),
])
def test_empty_or_thought_only_response_is_an_error(model_response):
    agent = configured_agent()
    agent._client.models.generate_content.return_value = model_response
    result = agent.query("deadlines today")
    assert result["answer"]
    assert result["steps"][-1]["type"] == "error"


@pytest.mark.parametrize("error", [httpx.ConnectTimeout(""), errors.ServerError(503, {})])
def test_transient_errors_retry_without_reexecuting_tools(error):
    agent = configured_agent()
    agent._client.models.generate_content.side_effect = [error, response(types.Part(text="OK"))]
    with patch("agent.artex_agent.time.sleep") as sleep:
        result = agent.query("deadlines today")
    assert result["answer"] == "OK"
    assert sleep.call_count == 1
    assert result["meta"]["tool_calls"] == 0


def test_permission_errors_are_not_retried():
    agent = configured_agent()
    agent._client.models.generate_content.side_effect = errors.ClientError(403, {})
    with patch("agent.artex_agent.time.sleep") as sleep:
        result = agent.query("deadlines today")
    sleep.assert_not_called()
    assert result["steps"][-1]["type"] == "error"


def test_declarations_and_argument_validation():
    bridge = InMemoryMCPBridge()
    declarations = bridge.get_tools()[0].function_declarations
    assert {d.name for d in declarations} == set(bridge.tool_names)
    assert next(d for d in declarations if d.name == "add_deadline").parameters_json_schema[
        "required"
    ] == ["course", "title", "due_date"]
    for args in ({"days_ahead": "seven"}, {"unexpected": True}, {"days_ahead": True}):
        result = bridge.call_tool("list_deadlines", args)
        assert not result["ok"]
        assert "Invalid tool arguments" in result["error"]
    assert not bridge.call_tool("unknown", {})["ok"]


def test_cleanup_does_not_mask_original_error():
    agent = configured_agent()
    agent._client.close.side_effect = RuntimeError("secret")
    agent.close()
    agent.close()
    assert not hasattr(agent, "_client")


@pytest.mark.parametrize("max_steps", [0, -1, True, 1.5])
def test_invalid_step_limit_is_rejected(max_steps):
    with pytest.raises(ValueError):
        ArtexAgent(max_steps=max_steps)
