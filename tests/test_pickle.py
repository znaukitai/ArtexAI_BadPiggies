"""Cloudpickle serialization tests for Vertex AI deployment."""

from unittest.mock import MagicMock, patch
import cloudpickle

from agent.campuspulse_agent import CampusPulseAgent


def test_agent_init_contains_only_primitives() -> None:
    agent = CampusPulseAgent(
        model="gemini-2.5-flash",
        project="aitu-campus",
        location="us-central1",
        max_steps=6,
    )
    for key, value in agent.__dict__.items():
        assert isinstance(
            value, (str, int, float, bool, type(None))
        ), f"Attribute '{key}' has non-primitive type {type(value)} before set_up()"


@patch("google.genai.Client")
def test_cloudpickle_roundtrip_and_setup(mock_genai_client: MagicMock) -> None:
    agent = CampusPulseAgent(
        model="gemini-2.5-flash",
        project="aitu-campus",
        location="us-central1",
        max_steps=5,
    )

    payload = cloudpickle.dumps(agent)
    assert isinstance(payload, bytes)
    assert len(payload) > 0

    restored: CampusPulseAgent = cloudpickle.loads(payload)
    assert restored.model == "gemini-2.5-flash"
    assert restored.project == "aitu-campus"
    assert restored.location == "us-central1"
    assert restored.max_steps == 5

    restored.set_up()
    assert hasattr(restored, "_bridge")
    assert hasattr(restored, "_client")
    assert "get_today" in restored._bridge.tool_names
    mock_genai_client.assert_called_once()
