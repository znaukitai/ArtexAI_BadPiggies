"""Deadline logic unit tests."""

from datetime import date
import pytest

from core.deadline_logic import (
    build_weekly_plan,
    calculate_urgency,
    enrich_and_filter_deadlines,
    parse_iso_date,
    parse_syllabus_candidates,
)


def test_parse_iso_date_valid() -> None:
    assert parse_iso_date("2026-10-18") == date(2026, 10, 18)
    assert parse_iso_date("2026-10-18T23:59:00") == date(2026, 10, 18)


def test_parse_iso_date_invalid() -> None:
    with pytest.raises(ValueError):
        parse_iso_date("18-10-2026")
    with pytest.raises(ValueError):
        parse_iso_date("")


def test_calculate_urgency_buckets() -> None:
    ref = date(2026, 10, 18)

    days_overdue, urg_overdue = calculate_urgency("2026-10-16", ref)
    assert days_overdue == -2
    assert urg_overdue == "overdue"

    days_today, urg_today = calculate_urgency("2026-10-18", ref)
    assert days_today == 0
    assert urg_today == "today"

    days_urgent, urg_urgent = calculate_urgency("2026-10-20", ref)
    assert days_urgent == 2
    assert urg_urgent == "urgent"

    days_normal, urg_normal = calculate_urgency("2026-10-25", ref)
    assert days_normal == 7
    assert urg_normal == "normal"


def test_enrich_and_filter_deadlines_sorting_and_filtering() -> None:
    ref = date(2026, 10, 18)
    raw = [
        {
            "id": "1",
            "course": "Golang Backend",
            "title": "Microservice Lab",
            "due_date": "2026-10-20",
            "priority": "medium",
            "status": "pending",
        },
        {
            "id": "2",
            "course": "Machine Learning",
            "title": "Gradient Boosting Report",
            "due_date": "2026-10-20",
            "priority": "critical",
            "status": "pending",
        },
        {
            "id": "3",
            "course": "Calculus",
            "title": "Done Homework",
            "due_date": "2026-10-19",
            "priority": "high",
            "status": "completed",
        },
    ]

    result = enrich_and_filter_deadlines(raw, reference_date=ref, days_ahead=5)
    assert len(result) == 2
    assert result[0]["id"] == "2"
    assert result[0]["urgency"] == "urgent"
    assert result[1]["id"] == "1"

    ml_only = enrich_and_filter_deadlines(raw, reference_date=ref, course="machine")
    assert len(ml_only) == 1
    assert ml_only[0]["course"] == "Machine Learning"


def test_build_weekly_plan_load_balancing() -> None:
    start = date(2026, 10, 18)
    raw = [
        {
            "id": "d1",
            "course": "AI Agents",
            "title": "MCP Server Implementation",
            "due_date": "2026-10-19",
            "priority": "critical",
            "status": "pending",
        },
        {
            "id": "d2",
            "course": "Computer Networks",
            "title": "Wireshark Packet Trace",
            "due_date": "2026-10-21",
            "priority": "high",
            "status": "pending",
        },
    ]

    plan = build_weekly_plan(raw, start_date=start)
    assert plan["start_date"] == "2026-10-18"
    assert plan["end_date"] == "2026-10-24"
    assert plan["total_scheduled_tasks"] == 2
    assert plan["total_estimated_hours"] == 7.0
    assert len(plan["days"]) == 7


def test_parse_syllabus_candidates() -> None:
    syllabus = """
CS301 - Lab 1 FastMCP Architecture due 2026-10-22 [high]
Linear Algebra: Quiz 3 - 2026-10-25 (medium)
Random note without any date
"""
    candidates = parse_syllabus_candidates(syllabus)
    assert len(candidates) == 2
    assert candidates[0]["course"] == "CS301"
    assert candidates[0]["due_date"] == "2026-10-22"
    assert candidates[0]["priority"] == "high"
    assert candidates[1]["course"] == "Linear Algebra"
    assert candidates[1]["due_date"] == "2026-10-25"


def test_russian_formatting_helpers() -> None:
    from core.deadline_logic import (
        format_date_ru,
        format_days_left_ru,
        format_priority_ru,
        format_urgency_ru,
    )

    assert format_days_left_ru(0) == "сегодня"
    assert format_days_left_ru(1) == "1 дн."
    assert format_days_left_ru(2) == "2 дн."
    assert format_days_left_ru(5) == "5 дн."
    assert format_days_left_ru(21) == "21 дн."
    assert format_days_left_ru(-1) == "просрочено на 1 дн."
    assert format_days_left_ru(-3) == "просрочено на 3 дн."

    assert format_priority_ru("critical") == "критично"
    assert format_priority_ru("high") == "высокий"
    assert format_priority_ru("medium") == "средний"
    assert format_priority_ru("low") == "низкий"

    assert format_urgency_ru("overdue") == "Просрочено"
    assert format_urgency_ru("today") == "Сегодня"
    assert format_urgency_ru("urgent") == "Срочно"
    assert format_urgency_ru("normal") == "В планах"

    assert format_date_ru("2026-10-20") == "20 окт"
    assert format_date_ru("2026-10-20", with_year=True) == "20 окт 2026"

