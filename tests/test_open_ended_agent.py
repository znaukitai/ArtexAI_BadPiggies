"""Queries are interpreted by Gemini rather than a local intent classifier."""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from agent.artex_agent import ArtexAgent
from agent.mcp_bridge import InMemoryMCPBridge
from agent.prompts import SYSTEM_INSTRUCTION
from frontend.gateway import CloudBackend, Gateway, GatewayError, LocalBackend


def model_response(*parts: types.Part) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=list(parts)), finish_reason="STOP",
    )])


def make_agent() -> ArtexAgent:
    agent = ArtexAgent(api_key="test-key")
    agent._client = MagicMock()
    agent._bridge = InMemoryMCPBridge()
    agent._system_instruction = SYSTEM_INSTRUCTION
    agent._backend_mode = "local"
    return agent


@pytest.mark.parametrize("prompt", [
    "Explain recursion using a cooking analogy.",
    "Расскажи шутку", "hello", "?", "аывджадв", "   ",
    "What is the weather?", "Help me write a kind apology.",
    "Explain why 'ignore previous instructions' can be a prompt injection.",
    "Summarize this syllabus: " + "Unusual content. " * 800,
])
def test_every_topic_reaches_model_unchanged(prompt):
    agent = make_agent()
    agent._client.models.generate_content.return_value = model_response(
        types.Part(text="A contextual answer or clarification.")
    )
    result = agent.query(prompt, {"deadlines": [], "custom": "preserved"})
    call = agent._client.models.generate_content.call_args
    assert call.kwargs["contents"][0].parts[0].text == prompt
    assert result["answer"] == "A contextual answer or clarification."
    assert result["meta"]["tool_calls"] == 0
    assert result["state"]["custom"] == "preserved"
    assert [step["type"] for step in result["steps"]] == ["final"]


@pytest.mark.parametrize("function_name, args", [
    ("unsupported_search", {"query": "weather"}),
    ("list_deadlines", {"days_ahead": "invalid"}),
])
def test_failed_tool_returns_to_model_for_helpful_answer(function_name, args):
    agent = make_agent()
    agent._client.models.generate_content.side_effect = [
        model_response(types.Part(function_call=types.FunctionCall(
            name=function_name, args=args, id="call-1",
        ))),
        model_response(types.Part(text="I cannot retrieve that data, but here is useful guidance.")),
    ]
    result = agent.query("Could you help me work this out?", {"deadlines": []})
    assert agent._client.models.generate_content.call_count == 2
    assert result["steps"][1]["result"]["ok"] is False
    assert result["steps"][-1]["type"] == "final"
    assert "useful guidance" in result["answer"]


def test_novel_request_can_dynamically_select_tools():
    agent = make_agent()
    agent._client.models.generate_content.side_effect = [
        model_response(types.Part(function_call=types.FunctionCall(name="get_today", args={}))),
        model_response(types.Part(text="Here is a starting point based on the current date.")),
    ]
    result = agent.query("I feel overwhelmed; can you help me decide where to begin?")
    assert result["meta"]["tool_calls"] == 1
    assert result["steps"][0]["name"] == "get_today"


@pytest.mark.parametrize("backend", ["local", "cloud"])
@pytest.mark.parametrize("prompt", ["hello", "Explain a rainbow.", "x" * 10001])
def test_gateway_routes_queries_to_agent(backend, prompt):
    with patch("agent.artex_agent.ArtexAgent") as cls:
        cls.return_value.query.return_value = {
            "answer": "Generated answer", "steps": [], "state": {"deadlines": []}, "meta": {},
        }
        gateway = Gateway(backend, api_key="test-key", project="test-project")
        if backend == "cloud":
            gateway.backend.url = None
        result = gateway.query(prompt, {"deadlines": []})
        assert result.answer == "Generated answer"
        cls.return_value.query.assert_called_once_with(user_input=prompt, state={"deadlines": []})
        cls.return_value.close.assert_called_once()


def test_remote_agent_engine_receives_unmatched_topic():
    backend = CloudBackend(resource="projects/test/locations/us-central1/reasoningEngines/123")
    payload = {"answer": "A generated explanation", "steps": [], "state": {}, "meta": {}}
    with patch("google.auth.default", return_value=(MagicMock(), "test")), patch(
        "google.auth.transport.requests.AuthorizedSession"
    ) as session:
        post = session.return_value.__enter__.return_value.post
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"output": payload}
        assert backend.query("Explain a rainbow.", {}).answer == payload["answer"]
        assert post.call_args.kwargs["json"]["input"]["user_input"] == "Explain a rainbow."


def test_missing_credentials_is_explicit_without_canned_answer(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(GatewayError, match="GEMINI_API_KEY"):
        LocalBackend().query("Explain a rainbow.", {})


def test_legacy_demo_mode_no_longer_bypasses_gemini():
    with patch("agent.artex_agent.ArtexAgent") as cls:
        backend = LocalBackend(mode="demo", api_key="test-key")
    assert backend.agent is cls.return_value
    assert not backend.is_demo
