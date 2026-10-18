"""MCP server for deadlines and weekly planning."""

from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mcp.server.fastmcp import FastMCP

from agent.models import DeadlineItem
from core.deadline_logic import (
    build_weekly_plan,
    calculate_urgency,
    enrich_and_filter_deadlines,
    parse_iso_date,
    parse_syllabus_candidates,
)

mcp = FastMCP("academic_schedule")

ALMATY_TZ_NAME = "Asia/Almaty"


def _now_almaty() -> datetime:
    try:
        tz = ZoneInfo(ALMATY_TZ_NAME)
        return datetime.now(tz)
    except ZoneInfoNotFoundError:
        from datetime import timezone

        return datetime.now(timezone(timedelta(hours=5)))


def _build_default_deadlines(reference_date: Optional[date] = None) -> List[Dict[str, Any]]:
    base = reference_date or _now_almaty().date()
    return [
        {
            "id": "dl-aitu-01",
            "course": "AI & LLM Engineering",
            "title": "Deploy Agent to Vertex AI Reasoning Engine",
            "due_date": (base + timedelta(days=2)).isoformat(),
            "priority": "critical",
            "status": "pending",
            "source": "demo",
        },
        {
            "id": "dl-aitu-02",
            "course": "Distributed Systems",
            "title": "Lab 4: gRPC & Raft Consensus",
            "due_date": (base + timedelta(days=4)).isoformat(),
            "priority": "high",
            "status": "pending",
            "source": "demo",
        },
        {
            "id": "dl-aitu-03",
            "course": "Advanced Algorithms",
            "title": "Dynamic Programming Problem Set",
            "due_date": (base + timedelta(days=7)).isoformat(),
            "priority": "medium",
            "status": "pending",
            "source": "demo",
        },
    ]


_DEFAULT_DEADLINES: List[Dict[str, Any]] = _build_default_deadlines()
_DEADLINE_STORE: List[Dict[str, Any]] = _build_default_deadlines()


def get_deadline_store() -> List[Dict[str, Any]]:
    return [dict(item) for item in _DEADLINE_STORE]


def get_default_deadlines(reference_date: Optional[date] = None) -> List[Dict[str, Any]]:
    return _build_default_deadlines(reference_date=reference_date)


def set_deadline_store(items: List[Dict[str, Any]]) -> None:
    global _DEADLINE_STORE
    validated: List[Dict[str, Any]] = []
    for raw in items:
        if isinstance(raw, dict):
            normalized = dict(raw)
            normalized.setdefault("course", "General")
            normalized.setdefault("priority", "medium")
            normalized.setdefault("source", "demo")
            if normalized.get("status") == "open":
                normalized["status"] = "pending"
            elif normalized.get("status") == "done":
                normalized["status"] = "completed"
            model = DeadlineItem.model_validate(normalized)
            validated.append(model.model_dump())
    _DEADLINE_STORE = validated


def reset_deadline_store(reference_date: Optional[date] = None) -> None:
    global _DEADLINE_STORE
    _DEADLINE_STORE = _build_default_deadlines(reference_date=reference_date)


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


@mcp.tool()
def get_today() -> Dict[str, Any]:
    """Get current date and time in Asia/Almaty timezone."""
    start_ns = time.perf_counter_ns()
    now = _now_almaty()
    return _make_response(
        ok=True,
        data={
            "date": now.date().isoformat(),
            "datetime": now.isoformat(timespec="seconds"),
            "weekday": now.strftime("%A"),
            "timezone": ALMATY_TZ_NAME,
            "utc_offset": "+05:00",
        },
        source="live",
        start_ns=start_ns,
    )


@mcp.tool()
def add_deadline(
    course: str,
    title: str,
    due_date: str,
    priority: Literal["low", "medium", "high", "critical"] = "medium",
) -> Dict[str, Any]:
    """Add a new deadline in YYYY-MM-DD format."""
    start_ns = time.perf_counter_ns()
    try:
        parse_iso_date(due_date)
        normalized_priority = priority.lower().strip()
        if normalized_priority not in ("low", "medium", "high", "critical"):
            raise ValueError("priority must be one of: low, medium, high, critical.")

        new_item = DeadlineItem(
            id=f"dl-{uuid.uuid4().hex[:8]}",
            course=course.strip(),
            title=title.strip(),
            due_date=due_date.strip(),
            priority=normalized_priority,  # type: ignore[arg-type]
            status="pending",
            source="live",
        )
        record = new_item.model_dump()
        _DEADLINE_STORE.append(record)

        ref_date = _now_almaty().date()
        days_left, urgency = calculate_urgency(record["due_date"], ref_date)
        enriched = {**record, "days_left": days_left, "urgency": urgency}

        return _make_response(
            ok=True,
            data={"added": enriched, "total_count": len(_DEADLINE_STORE)},
            source="live",
            start_ns=start_ns,
        )
    except Exception as exc:
        return _make_response(
            ok=False,
            data=None,
            error=str(exc),
            source="live",
            start_ns=start_ns,
        )


@mcp.tool()
def list_deadlines(
    days_ahead: Optional[int] = 30,
    course: Optional[str] = None,
) -> Dict[str, Any]:
    """List pending deadlines sorted by urgency."""
    start_ns = time.perf_counter_ns()
    try:
        ref_date = _now_almaty().date()
        items = enrich_and_filter_deadlines(
            deadlines=_DEADLINE_STORE,
            reference_date=ref_date,
            days_ahead=days_ahead,
            course=course,
            include_completed=False,
        )
        return _make_response(
            ok=True,
            data={
                "reference_date": ref_date.isoformat(),
                "count": len(items),
                "deadlines": items,
            },
            source="demo",
            start_ns=start_ns,
        )
    except Exception as exc:
        return _make_response(
            ok=False,
            data=None,
            error=str(exc),
            source="demo",
            start_ns=start_ns,
        )


@mcp.tool()
def plan_week(start_date: Optional[str] = None) -> Dict[str, Any]:
    """Generate a 7-day study plan across active deadlines."""
    start_ns = time.perf_counter_ns()
    try:
        base_date: date = (
            parse_iso_date(start_date) if start_date else _now_almaty().date()
        )
        plan = build_weekly_plan(deadlines=_DEADLINE_STORE, start_date=base_date)
        return _make_response(
            ok=True,
            data=plan,
            source="demo",
            start_ns=start_ns,
        )
    except Exception as exc:
        return _make_response(
            ok=False,
            data=None,
            error=str(exc),
            source="demo",
            start_ns=start_ns,
        )


@mcp.tool()
def parse_syllabus_text(text: str) -> Dict[str, Any]:
    """Preview candidate deadlines from syllabus text without saving."""
    start_ns = time.perf_counter_ns()
    try:
        candidates = parse_syllabus_candidates(text)
        return _make_response(
            ok=True,
            data={
                "candidates_count": len(candidates),
                "candidates": candidates,
                "saved": False,
                "notice": "Candidates extracted for preview only. Call add_deadline after user confirmation.",
            },
            source="live",
            start_ns=start_ns,
        )
    except Exception as exc:
        return _make_response(
            ok=False,
            data=None,
            error=str(exc),
            source="live",
            start_ns=start_ns,
        )
