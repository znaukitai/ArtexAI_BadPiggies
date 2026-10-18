"""Agent reasoning loop with multi-step tool calls."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent.mcp_bridge import InMemoryMCPBridge
from agent.models import AgentResponse, SourceType, Step
from agent.prompts import SYSTEM_INSTRUCTION


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class CampusPulseAgent:
    """Student assistant agent compatible with Vertex AI Agent Engine."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        project: Optional[str] = None,
        location: Optional[str] = None,
        model_location: Optional[str] = None,
        max_steps: int = 6,
    ) -> None:
        # Primitive types only for cloudpickle serialization
        self.model: str = str(model)
        self.project: Optional[str] = str(project) if project else None
        self.location: Optional[str] = str(location) if location else None
        self.model_location: Optional[str] = str(model_location) if model_location else None
        self.max_steps: int = int(max_steps)

    def set_up(self) -> None:
        from google import genai

        self._bridge = InMemoryMCPBridge()
        self._system_instruction = SYSTEM_INSTRUCTION

        resolved_project = self.project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        resolved_location = (
            self.model_location
            or os.environ.get("GOOGLE_CLOUD_MODEL_LOCATION")
            or self.location
            or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if resolved_project and not api_key:
            self._client = genai.Client(
                vertexai=True,
                project=resolved_project,
                location=resolved_location,
            )
            self._backend_mode = "cloud"
        elif api_key:
            self._client = genai.Client(api_key=api_key)
            self._backend_mode = "local"
        else:
            self._client = genai.Client(
                vertexai=True,
                project=resolved_project,
                location=resolved_location,
            )
            self._backend_mode = "cloud"

    def _ensure_setup(self) -> None:
        if not hasattr(self, "_bridge") or not hasattr(self, "_client"):
            self.set_up()

    def _call_model_with_retry(
        self,
        contents: List[Any],
        config: Any,
        max_retries: int = 3,
    ) -> Any:
        delay = 1.0
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                return self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                last_exc = exc
                err_text = str(exc).lower()
                is_transient = any(
                    k in err_text
                    for k in ("429", "resource_exhausted", "rate limit", "503", "timeout", "connection")
                )
                if not is_transient or attempt == max_retries - 1:
                    raise
                time.sleep(delay)
                delay *= 2.0
        if last_exc:
            raise last_exc
        raise RuntimeError("Unreachable retry state")

    def query(
        self,
        user_input: str,
        state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from google.genai import types

        query_start_ns = time.perf_counter_ns()
        self._ensure_setup()

        active_session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
        self._bridge.sync_state_before_query(state)

        steps: List[Step] = []
        step_index = 0
        tool_calls_count = 0

        if not user_input or not str(user_input).strip():
            empty_step = Step(
                index=0,
                type="error",
                thought="Empty user input received.",
                started_at=_utc_iso_now(),
                duration_ms=0,
            )
            resp = AgentResponse(
                answer="Пожалуйста, введите ваш запрос.",
                steps=[empty_step],
                state=self._bridge.export_state_after_query(state),
                meta={
                    "model": self.model,
                    "session_id": active_session_id,
                    "total_ms": 0,
                    "tool_calls": 0,
                    "steps_count": 1,
                    "backend": getattr(self, "_backend_mode", "local"),
                },
            )
            return resp.model_dump()

        contents: List[Any] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=str(user_input))],
            )
        ]

        config_values: Dict[str, Any] = {
            "system_instruction": self._system_instruction,
            "tools": self._bridge.get_callable_tools(),
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }
        if not self.model.startswith("gemini-3."):
            config_values["temperature"] = 0.1
        gen_config = types.GenerateContentConfig(**config_values)

        final_answer = ""

        try:
            for _iteration in range(self.max_steps):
                llm_start_ns = time.perf_counter_ns()
                llm_started_at = _utc_iso_now()

                response = self._call_model_with_retry(contents=contents, config=gen_config)
                llm_duration_ms = max(0, int((time.perf_counter_ns() - llm_start_ns) / 1_000_000))

                candidate = response.candidates[0] if getattr(response, "candidates", None) else None
                model_content = getattr(candidate, "content", None)
                parts = getattr(model_content, "parts", None) or []

                if model_content is not None:
                    contents.append(model_content)

                text_fragments: List[str] = []
                function_calls: List[Any] = []

                for part in parts:
                    if getattr(part, "text", None):
                        text_fragments.append(part.text)
                    if getattr(part, "function_call", None):
                        function_calls.append(part.function_call)

                if not function_calls and getattr(response, "function_calls", None):
                    function_calls = list(response.function_calls)

                combined_text = "\n".join(t.strip() for t in text_fragments if t.strip()).strip()

                if function_calls:
                    if combined_text:
                        steps.append(
                            Step(
                                index=step_index,
                                type="thought",
                                thought="Подготовка вызова инструмента.",
                                started_at=llm_started_at,
                                duration_ms=llm_duration_ms,
                            )
                        )
                        step_index += 1

                    tool_response_parts: List[Any] = []

                    for fc in function_calls:
                        tool_name = str(getattr(fc, "name", ""))
                        raw_args = getattr(fc, "args", None)
                        tool_args: Dict[str, Any] = dict(raw_args) if raw_args else {}

                        call_started_at = _utc_iso_now()
                        steps.append(
                            Step(
                                index=step_index,
                                type="tool_call",
                                name=tool_name,
                                args=tool_args,
                                thought=f"Calling '{tool_name}'",
                                started_at=call_started_at,
                                duration_ms=0,
                            )
                        )
                        step_index += 1
                        tool_calls_count += 1

                        result_started_at = _utc_iso_now()
                        envelope = self._bridge.call_tool(tool_name, tool_args)
                        source_val: SourceType = (
                            "demo" if envelope.get("source") == "demo" else "live"
                        )

                        steps.append(
                            Step(
                                index=step_index,
                                type="tool_result",
                                name=tool_name,
                                args=tool_args,
                                result=envelope,
                                source=source_val,
                                started_at=result_started_at,
                                duration_ms=int(envelope.get("elapsed_ms", 0)),
                            )
                        )
                        step_index += 1

                        tool_response_parts.append(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"result": envelope},
                            )
                        )

                    contents.append(
                        types.Content(
                            role="user",
                            parts=tool_response_parts,
                        )
                    )
                    continue

                final_answer = combined_text or getattr(response, "text", "") or ""
                steps.append(
                    Step(
                        index=step_index,
                        type="final",
                        thought="Response ready.",
                        started_at=llm_started_at,
                        duration_ms=llm_duration_ms,
                    )
                )
                step_index += 1
                break
            else:
                final_answer = (
                    "Достигнут лимит шагов (max_steps). "
                    "Пожалуйста, уточните запрос или разбейте задачу на части."
                )
                steps.append(
                    Step(
                        index=step_index,
                        type="error",
                        thought=f"Reached max_steps={self.max_steps} limit.",
                        started_at=_utc_iso_now(),
                        duration_ms=0,
                    )
                )
                step_index += 1

        except Exception as exc:
            final_answer = "Не удалось выполнить запрос к модели. Проверьте ключ API или настройки подключения."
            steps.append(
                Step(
                    index=step_index,
                    type="error",
                    thought=f"Execution error: {exc}",
                    started_at=_utc_iso_now(),
                    duration_ms=0,
                )
            )
            step_index += 1

        total_ms = max(0, int((time.perf_counter_ns() - query_start_ns) / 1_000_000))
        updated_state = self._bridge.export_state_after_query(state)

        agent_response = AgentResponse(
            answer=final_answer,
            steps=steps,
            state=updated_state,
            meta={
                "model": self.model,
                "session_id": active_session_id,
                "total_ms": total_ms,
                "tool_calls": tool_calls_count,
                "steps_count": len(steps),
                "backend": getattr(self, "_backend_mode", "local"),
            },
        )
        return agent_response.model_dump()
