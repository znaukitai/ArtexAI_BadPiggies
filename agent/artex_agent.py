"""Agent reasoning loop with multi-step tool calls."""

from __future__ import annotations

import os
import logging
import random
import time
import uuid
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.genai import types

from core.input_normalization import normalize_api_key
from agent.mcp_bridge import InMemoryMCPBridge
from agent.models import AgentResponse, SourceType, Step
from agent.prompts import SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _classify_api_error(exc: Exception, model: str) -> str:
    """Produce a safe, user-readable error summary without leaking secrets."""
    # httpx.ConnectTimeout may have an empty message. Inspect its type and causes.
    current = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (httpx.TimeoutException, TimeoutError)):
            return "Нет связи с сервером Google: время ожидания истекло. Проверьте сеть, VPN и прокси. Проверка API-ключа не завершена."
        if isinstance(current, (httpx.NetworkError, httpx.ProxyError, ConnectionError)):
            return "Нет связи с сервером Google. Проверьте сеть, VPN и прокси. Проверка API-ключа не завершена."
        current = current.__cause__ or current.__context__
    raw = str(exc)
    lower = (type(exc).__name__ + " " + raw).lower()
    if "404" in lower or "not_found" in lower or "not found" in lower:
        return f"Модель '{model}' не найдена (HTTP 404). Проверьте название модели в настройках."
    if "401" in lower or "403" in lower or "api_key_invalid" in lower or "invalid api key" in lower or "permission_denied" in lower:
        return "Неверный ключ Gemini API или доступ запрещён (HTTP 401/403)."
    if "429" in lower or "resource_exhausted" in lower or "quota" in lower or "rate limit" in lower:
        return "Превышен лимит запросов или квота Gemini API (HTTP 429)."
    if "timeout" in lower or "connect" in lower or "network" in lower:
        return "Ошибка сети при обращении к Gemini API. Проверьте подключение к интернету."
    return "Ошибка при вызове модели Gemini API. Проверьте ключ и настройки."


class ArtexAgent:
    """Student assistant agent compatible with Vertex AI Agent Engine."""

    def __init__(
        self,
        model: str = DEFAULT_GEMINI_MODEL,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model_location: Optional[str] = None,
        max_steps: int = 6,
        api_key: Optional[str] = None,
    ) -> None:
        # Primitive types only for cloudpickle serialization
        self.model: str = str(model) if model else DEFAULT_GEMINI_MODEL
        self.project: Optional[str] = str(project) if project else None
        self.location: Optional[str] = str(location) if location else None
        self.model_location: Optional[str] = str(model_location) if model_location else None
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps: int = max_steps
        self._api_key_override: Optional[str] = normalize_api_key(api_key) or None

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
        api_key = (
            getattr(self, "_api_key_override", None)
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

        options = types.HttpOptions(timeout=60_000)
        # An explicitly selected cloud project must not be overridden by a local key.
        if self.project or (resolved_project and not api_key):
            self._client = genai.Client(
                vertexai=True, project=resolved_project,
                location=resolved_location, http_options=options,
            )
            self._backend_mode = "cloud"
        elif api_key:
            self._client = genai.Client(
                vertexai=False, api_key=normalize_api_key(api_key), http_options=options,
            )
            self._backend_mode = "local"
        else:
            raise ValueError("Configure GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT.")

    def close(self) -> None:
        client = getattr(self, "_client", None)
        if client is not None:
            try:
                client.close()
            except Exception as exc:
                logger.warning("Gemini client cleanup failed (%s)", type(exc).__name__)
            finally:
                del self._client

    def _ensure_setup(self) -> None:
        if not hasattr(self, "_bridge") or not hasattr(self, "_client"):
            self.set_up()

    def _call_model_with_retry(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
        max_retries: int = 3,
    ) -> types.GenerateContentResponse:
        if max_retries < 1:
            raise ValueError("max_retries must be positive")
        delay = 1.0
        last_exc: Optional[Exception] = None
        current_model = self.model
        for attempt in range(max_retries):
            try:
                return self._client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                last_exc = exc
                code = getattr(exc, "code", None)
                is_transient = (
                    code in {408, 429, 500, 502, 503, 504}
                    or isinstance(exc, (httpx.TimeoutException, httpx.NetworkError,
                                        httpx.ProxyError, TimeoutError, ConnectionError))
                )
                logger.warning(
                    "Gemini request failed: model=%s attempt=%d/%d error=%s retryable=%s",
                    self.model, attempt + 1, max_retries, type(exc).__name__, is_transient,
                )
                if not is_transient or attempt == max_retries - 1:
                    raise
                time.sleep(delay + random.uniform(0, delay * 0.25))
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
        if not hasattr(self, "_bridge"):
            self._bridge = InMemoryMCPBridge()

        active_session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
        self._bridge.sync_state_before_query(state)

        steps: List[Step] = []
        step_index = 0
        tool_calls_count = 0

        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=str(user_input))],
            )
        ]

        final_answer = ""

        try:
            self._ensure_setup()
            config_values: Dict[str, Any] = {
                "system_instruction": self._system_instruction,
                "tools": self._bridge.get_tools(),
                "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
            }
            if not self.model.startswith("gemini-3."):
                config_values["temperature"] = 0.1
            gen_config = types.GenerateContentConfig(**config_values)
            for _iteration in range(self.max_steps):
                llm_start_ns = time.perf_counter_ns()
                llm_started_at = _utc_iso_now()

                response = self._call_model_with_retry(contents=contents, config=gen_config)
                llm_duration_ms = max(0, int((time.perf_counter_ns() - llm_start_ns) / 1_000_000))

                candidate = response.candidates[0] if getattr(response, "candidates", None) else None
                model_content = getattr(candidate, "content", None)
                parts = getattr(model_content, "parts", None) or []
                if not parts:
                    raise RuntimeError("Gemini returned no usable content (blocked or empty response).")

                if model_content is not None:
                    contents.append(model_content)

                text_fragments: List[str] = []
                function_calls: list[types.FunctionCall] = []

                for part in parts:
                    if getattr(part, "text", None) and not getattr(part, "thought", False):
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
                                source="live",
                                started_at=llm_started_at,
                                duration_ms=llm_duration_ms,
                            )
                        )
                        step_index += 1

                    tool_response_parts: list[types.Part] = []

                    for fc in function_calls:
                        tool_name = str(getattr(fc, "name", ""))
                        raw_args = getattr(fc, "args", None)
                        tool_args: Dict[str, Any] = dict(raw_args) if raw_args else {}

                        call_started_at = _utc_iso_now()
                        result_started_at = _utc_iso_now()
                        envelope = self._bridge.call_tool(tool_name, tool_args)
                        source_val: SourceType = (
                            "demo" if envelope.get("source") == "demo" else "live"
                        )

                        steps.append(
                            Step(
                                index=step_index,
                                type="tool_call",
                                name=tool_name,
                                args=tool_args,
                                thought=f"Вызов инструмента '{tool_name}'",
                                source=source_val,
                                started_at=call_started_at,
                                duration_ms=0,
                            )
                        )
                        step_index += 1
                        tool_calls_count += 1

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
                            types.Part(function_response=types.FunctionResponse(
                                id=getattr(fc, "id", None),
                                name=tool_name,
                                response={"result": envelope},
                            ))
                        )

                    contents.append(
                        types.Content(
                            role="user",
                            parts=tool_response_parts,
                        )
                    )
                    continue

                final_answer = combined_text
                if not final_answer:
                    raise RuntimeError("Gemini returned no visible answer or function calls.")
                steps.append(
                    Step(
                        index=step_index,
                        type="final",
                        thought="Ответ сформирован.",
                        source="live",
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
                        source="live",
                        started_at=_utc_iso_now(),
                        duration_ms=0,
                    )
                )
                step_index += 1

        except Exception as exc:
            logger.error("Gemini query failed: model=%s error=%s", self.model, type(exc).__name__)
            err_summary = _classify_api_error(exc, self.model)
            final_answer = err_summary
            steps.append(
                Step(
                    index=step_index,
                    type="error",
                    thought=err_summary,
                    source="live",
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
