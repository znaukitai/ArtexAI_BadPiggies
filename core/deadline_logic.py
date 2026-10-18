"""Deadline parsing, urgency calculation, and weekly schedule planning."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Tuple

UrgencyLevel = Literal["overdue", "today", "urgent", "normal"]
PriorityLevel = Literal["low", "medium", "high", "critical"]

PRIORITY_WEIGHTS: Dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

ESTIMATED_HOURS_BY_PRIORITY: Dict[str, float] = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}


def parse_iso_date(date_str: str) -> date:
    """Parse YYYY-MM-DD or ISO datetime string into a date."""
    if not isinstance(date_str, str) or not date_str.strip():
        raise ValueError("due_date must be a non-empty ISO 8601 string.")

    cleaned = date_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        if "T" in cleaned or " " in cleaned:
            return datetime.fromisoformat(cleaned).date()
        return date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(
            f"Invalid ISO 8601 date format '{date_str}'. Expected YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS."
        ) from exc


def calculate_urgency(due_date_str: str, reference_date: date) -> Tuple[int, UrgencyLevel]:
    """Return remaining days and urgency tag relative to reference_date."""
    target_date = parse_iso_date(due_date_str)
    days_left = (target_date - reference_date).days

    if days_left < 0:
        urgency: UrgencyLevel = "overdue"
    elif days_left == 0:
        urgency = "today"
    elif days_left <= 3:
        urgency = "urgent"
    else:
        urgency = "normal"

    return days_left, urgency


def enrich_and_filter_deadlines(
    deadlines: List[Dict[str, Any]],
    reference_date: date,
    days_ahead: Optional[int] = None,
    course: Optional[str] = None,
    include_completed: bool = False,
) -> List[Dict[str, Any]]:
    """Add days_left and urgency to deadlines, then filter and sort."""
    enriched: List[Dict[str, Any]] = []
    course_filter = course.strip().lower() if course else None

    for item in deadlines:
        status = item.get("status", "pending")
        if not include_completed and status in ("completed", "done"):
            continue

        item_course = str(item.get("course", ""))
        if course_filter and course_filter not in item_course.lower():
            continue

        due_date_str = str(item.get("due_date", ""))
        days_left, urgency = calculate_urgency(due_date_str, reference_date)

        if days_ahead is not None and days_left > days_ahead:
            continue

        record = dict(item)
        record["days_left"] = days_left
        record["urgency"] = urgency
        enriched.append(record)

    enriched.sort(
        key=lambda x: (
            x["days_left"],
            -PRIORITY_WEIGHTS.get(str(x.get("priority", "medium")).lower(), 2),
            str(x.get("title", "")),
        )
    )
    return enriched


def build_weekly_plan(
    deadlines: List[Dict[str, Any]],
    start_date: date,
    max_daily_hours: float = 6.0,
) -> Dict[str, Any]:
    """Spread pending deadlines across a 7-day window."""
    days_map: Dict[str, Dict[str, Any]] = {}
    day_keys: List[str] = []

    for offset in range(7):
        current_day = start_date + timedelta(days=offset)
        iso_day = current_day.isoformat()
        day_keys.append(iso_day)
        days_map[iso_day] = {
            "date": iso_day,
            "weekday": current_day.strftime("%A"),
            "allocated_hours": 0.0,
            "tasks": [],
        }

    relevant = enrich_and_filter_deadlines(
        deadlines=deadlines,
        reference_date=start_date,
        days_ahead=14,
        include_completed=False,
    )

    unassigned: List[Dict[str, Any]] = []

    for task in relevant:
        priority = str(task.get("priority", "medium")).lower()
        needed_hours = ESTIMATED_HOURS_BY_PRIORITY.get(priority, 2.0)
        days_left = int(task["days_left"])

        latest_index = 0 if days_left <= 0 else min(days_left, 6)
        candidate_days = day_keys[: latest_index + 1]
        best_day_key = min(
            candidate_days,
            key=lambda k: (days_map[k]["allocated_hours"], k),
        )

        if days_map[best_day_key]["allocated_hours"] + needed_hours <= max_daily_hours or best_day_key == day_keys[0]:
            days_map[best_day_key]["allocated_hours"] = round(
                days_map[best_day_key]["allocated_hours"] + needed_hours, 1
            )
            days_map[best_day_key]["tasks"].append(
                {
                    "id": task.get("id", ""),
                    "course": task.get("course", ""),
                    "title": task.get("title", ""),
                    "due_date": task.get("due_date", ""),
                    "priority": priority,
                    "urgency": task.get("urgency", "normal"),
                    "estimated_hours": needed_hours,
                }
            )
        else:
            unassigned.append(task)

    total_hours = sum(d["allocated_hours"] for d in days_map.values())
    total_tasks = sum(len(d["tasks"]) for d in days_map.values())

    return {
        "start_date": start_date.isoformat(),
        "end_date": (start_date + timedelta(days=6)).isoformat(),
        "total_scheduled_tasks": total_tasks,
        "total_estimated_hours": round(total_hours, 1),
        "days": [days_map[k] for k in day_keys],
        "overflow_tasks": unassigned,
    }


def parse_syllabus_candidates(text: str, default_course: str = "General") -> List[Dict[str, Any]]:
    """Extract candidate deadlines from raw syllabus text."""
    if not text or not text.strip():
        return []

    candidates: List[Dict[str, Any]] = []
    iso_pattern = re.compile(
        r"(?P<date>\b20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?:T\d{2}:\d{2}(?::\d{2})?)?\b)"
    )
    priority_pattern = re.compile(r"\b(critical|high|medium|low)\b", re.IGNORECASE)
    course_prefix_pattern = re.compile(r"^([A-Z]{2,6}\s?-?\s?\d{3}|[A-Za-zА-Яа-я0-9_ ]{2,25}):\s*(.+)$")

    for raw_line in text.splitlines():
        line = raw_line.strip(" \t•-*")
        if not line:
            continue

        date_match = iso_pattern.search(line)
        if not date_match:
            continue

        extracted_date = date_match.group("date")
        try:
            parse_iso_date(extracted_date)
        except ValueError:
            continue

        priority_match = priority_pattern.search(line)
        priority: PriorityLevel = (
            priority_match.group(1).lower()  # type: ignore[assignment]
            if priority_match
            else "medium"
        )

        cleaned = line.replace(extracted_date, "")
        if priority_match:
            cleaned = re.sub(
                r"[\[\(]?\b" + re.escape(priority_match.group(0)) + r"\b[\]\)]?",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
        cleaned = re.sub(r"\b(due|deadline|by|до|дедлайн)\b[:\s-]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip(" -–—:|,;")

        course = default_course
        title = cleaned or "Untitled Assignment"

        if " - " in cleaned:
            parts = [p.strip() for p in cleaned.split(" - ", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                course, title = parts[0], parts[1]
        else:
            prefix_match = course_prefix_pattern.match(cleaned)
            if prefix_match:
                course = prefix_match.group(1).strip()
                title = prefix_match.group(2).strip()

        candidates.append(
            {
                "id": f"cand-{uuid.uuid4().hex[:8]}",
                "course": course,
                "title": title,
                "due_date": extracted_date,
                "priority": priority,
                "status": "pending",
            }
        )

    return candidates


PRIORITY_RU: Dict[str, str] = {
    "critical": "критично",
    "high": "высокий",
    "medium": "средний",
    "low": "низкий",
}

URGENCY_RU: Dict[str, str] = {
    "overdue": "Просрочено",
    "today": "Сегодня",
    "urgent": "Срочно",
    "normal": "В планах",
}

MONTH_RU: Dict[int, str] = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "мая",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}


def format_date_ru(date_str: str, with_year: bool = False) -> str:
    """Format ISO date YYYY-MM-DD into Russian short format like '20 окт' or '20 окт 2026'."""
    try:
        dt = parse_iso_date(str(date_str).strip())
        mon = MONTH_RU.get(dt.month, "")
        return f"{dt.day} {mon} {dt.year}" if with_year else f"{dt.day} {mon}"
    except ValueError:
        return str(date_str)


def format_days_left_ru(days_left: int) -> str:
    """Format remaining days into standard Russian label."""
    if days_left < 0:
        return f"просрочено на {abs(days_left)} дн."
    if days_left == 0:
        return "сегодня"
    return f"{days_left} дн."


def format_priority_ru(priority: str) -> str:
    """Translate English priority code into Russian."""
    raw = str(priority).strip().lower()
    if raw in PRIORITY_RU.values():
        return raw
    return PRIORITY_RU.get(raw, "средний")


def format_urgency_ru(urgency: str) -> str:
    """Translate urgency bucket into Russian label."""
    raw = str(urgency).strip().lower()
    return URGENCY_RU.get(raw, "В планах")


def complete_deadline(
    deadlines: List[Dict[str, Any]],
    deadline_id: str,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Mark a deadline as completed by ID without mutating input records."""
    updated: List[Dict[str, Any]] = []
    found = False
    target = str(deadline_id).strip()
    for item in deadlines:
        if not isinstance(item, dict):
            continue
        copy_item = dict(item)
        if str(copy_item.get("id", "")) == target:
            copy_item["status"] = "completed"
            found = True
        updated.append(copy_item)
    return updated, found


def delete_deadline(
    deadlines: List[Dict[str, Any]],
    deadline_id: str,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Remove a deadline by ID and return (remaining_deadlines, found)."""
    updated: List[Dict[str, Any]] = []
    found = False
    target = str(deadline_id).strip()
    for item in deadlines:
        if not isinstance(item, dict):
            continue
        if str(item.get("id", "")) == target:
            found = True
            continue
        updated.append(dict(item))
    return updated, found


def group_deadlines_by_horizon(
    deadlines: List[Dict[str, Any]],
    reference_date: date,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group active deadlines into overdue, today, this_week, and later buckets."""
    enriched = enrich_and_filter_deadlines(
        deadlines=deadlines,
        reference_date=reference_date,
        days_ahead=None,
        include_completed=False,
    )
    groups: Dict[str, List[Dict[str, Any]]] = {
        "overdue": [],
        "today": [],
        "this_week": [],
        "later": [],
    }
    for task in enriched:
        days_left = int(task.get("days_left", 0))
        if days_left < 0:
            groups["overdue"].append(task)
        elif days_left == 0:
            groups["today"].append(task)
        elif days_left <= 7:
            groups["this_week"].append(task)
        else:
            groups["later"].append(task)
    return groups


