"""In-memory tool bridge."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from mcp_servers import academic_schedule, campus_services


class InMemoryMCPBridge:
    """Direct registry for tool functions."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Dict[str, Any]]] = {
            "get_today": academic_schedule.get_today,
            "add_deadline": academic_schedule.add_deadline,
            "list_deadlines": academic_schedule.list_deadlines,
            "plan_week": academic_schedule.plan_week,
            "parse_syllabus_text": academic_schedule.parse_syllabus_text,
            "github_repo_status": campus_services.github_repo_status,
            "github_assignment_check": campus_services.github_assignment_check,
            "find_campus_place": campus_services.find_campus_place,
        }

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_callable_tools(self) -> List[Callable[..., Any]]:
        return list(self._tools.values())

    def sync_state_before_query(self, state: Optional[Dict[str, Any]]) -> None:
        if state and isinstance(state.get("deadlines"), list):
            academic_schedule.set_deadline_store(state["deadlines"])

    def export_state_after_query(self, base_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        updated = dict(base_state) if base_state else {}
        updated["deadlines"] = academic_schedule.get_deadline_store()
        return updated

    def call_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start_ns = time.perf_counter_ns()
        if name not in self._tools:
            elapsed_ms = max(0, int((time.perf_counter_ns() - start_ns) / 1_000_000))
            return {
                "ok": False,
                "data": None,
                "error": f"Unknown tool '{name}'. Available: {', '.join(self.tool_names)}",
                "source": "live",
                "elapsed_ms": elapsed_ms,
            }

        fn = self._tools[name]
        safe_args = dict(args) if isinstance(args, dict) else {}
        try:
            result = fn(**safe_args)
            if isinstance(result, dict) and "ok" in result and "source" in result:
                return result
            elapsed_ms = max(0, int((time.perf_counter_ns() - start_ns) / 1_000_000))
            return {
                "ok": True,
                "data": result,
                "error": None,
                "source": "live",
                "elapsed_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = max(0, int((time.perf_counter_ns() - start_ns) / 1_000_000))
            return {
                "ok": False,
                "data": None,
                "error": f"Tool error in '{name}': {exc}",
                "source": "live",
                "elapsed_ms": elapsed_ms,
            }
