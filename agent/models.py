"""Pydantic models for agent state and responses."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

StepType = Literal["thought", "tool_call", "tool_result", "final", "error"]
SourceType = Literal["live", "demo"]


class Step(BaseModel):
    """Single step in agent execution."""

    index: int
    type: StepType
    name: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    thought: Optional[str] = None
    source: Optional[SourceType] = None
    started_at: str
    duration_ms: Optional[int] = None


class DeadlineItem(BaseModel):
    """Academic deadline record."""

    id: str
    course: str
    title: str
    due_date: str
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["pending", "completed"] = "pending"


class AgentResponse(BaseModel):
    """Response payload from CampusPulseAgent.query()."""

    answer: str
    steps: List[Step]
    state: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model": "",
            "session_id": "",
            "total_ms": 0,
            "tool_calls": 0,
            "steps_count": 0,
            "backend": "local",
        }
    )
