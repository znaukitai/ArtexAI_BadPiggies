"""UI gateway connecting Streamlit with local Gemini agent and Vertex AI."""

from __future__ import annotations

import copy
import importlib
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
ZONE = ZoneInfo("Asia/Almaty")
DEFAULT_REPO = "https://github.com/znaukitai/CampusPulseAI_BadPiggies.git"
DEFAULT_MODEL = "gemini-3.8-flash"

PRIORITY_RU = {
    "critical": "критично",
    "high": "высокий",
    "medium": "средний",
    "low": "низкий",
}

WEEKDAY_RU = {
    "Monday": "Пн",
    "Tuesday": "Вт",
    "Wednesday": "Ср",
    "Thursday": "Чт",
    "Friday": "Пт",
    "Saturday": "Сб",
    "Sunday": "Вс",
}

MONTH_RU = {
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
    """Format ISO date YYYY-MM-DD into Russian short format like '20 окт'."""
    try:
        dt = datetime.fromisoformat(str(date_str).strip()[:10]).date()
        mon = MONTH_RU.get(dt.month, "")
        return f"{dt.day} {mon} {dt.year}" if with_year else f"{dt.day} {mon}"
    except ValueError:
        return str(date_str)


def format_days_left_ru(days_left: int) -> str:
    """Format days remaining into standard Russian label."""
    if days_left < 0:
        return f"просрочено на {abs(days_left)} дн."
    if days_left == 0:
        return "сегодня"
    return f"{days_left} дн."


def format_priority_ru(priority: str) -> str:
    """Translate English priority code into Russian."""
    return PRIORITY_RU.get(str(priority).strip().lower(), "средний")


class GatewayError(RuntimeError):
    """User-facing error message."""


class _Step(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    type: Literal["thought", "tool_call", "tool_result", "final", "error"]
    name: str | None = None
    args: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    thought: str | None = None
    source: Literal["live", "demo"] | None = None
    started_at: str
    duration_ms: int | None = Field(default=None, ge=0)


class _AgentResponse(BaseModel):
    answer: str
    steps: list[_Step]
    state: dict[str, Any]
    meta: dict[str, Any]


try:
    from agent.models import AgentResponse
except ModuleNotFoundError:
    AgentResponse = _AgentResponse  # type: ignore[misc,assignment]

from agent.artex_agent import _classify_api_error
from core.input_normalization import normalize_api_key
from mcp_servers.academic_schedule import get_default_deadlines

_QUERY_LOCK = threading.RLock()


def validate_response(value: Any) -> AgentResponse:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    try:
        return AgentResponse.model_validate(value)
    except (ValueError, TypeError) as exc:
        raise GatewayError("Некорректный формат ответа от агента.") from exc


def demo_state() -> dict[str, Any]:
    return {"deadlines": get_default_deadlines()}


class LocalBackend:
    """Routes every query to Gemini when credentials are configured."""

    def __init__(self, mode: str | None = None, api_key: str | None = None) -> None:
        # Never mutate os.environ with user-entered key; keep in instance memory only
        self._api_key = normalize_api_key(api_key) or normalize_api_key(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        # Retain the legacy mode argument for callers; all modes now use Gemini.

        raw_model = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
        self.model = raw_model
        self.agent = None
        self.last_error: str | None = None

        has_credentials = bool(self._api_key)
        if has_credentials:
            try:
                module = importlib.import_module("agent.artex_agent")
                self.agent = module.ArtexAgent(
                    model=self.model,
                    api_key=self._api_key,
                )
            except Exception as exc:
                self.last_error = "Ошибка инициализации агента Gemini."
                raise GatewayError(self.last_error) from exc

        if self.agent:
            self.status = "Gemini не подключён: проверка ещё не выполнена"
            self.mode_kind = "gemini"
        else:
            self.status = "Gemini не подключён: ключ не указан"
            self.mode_kind = "error"

    @property
    def is_demo(self) -> bool:
        return False

    def query(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
        if self.agent:
            with _QUERY_LOCK:
                try:
                    result = self.agent.query(user_input=user_input, state=copy.deepcopy(state))
                except Exception as exc:
                    self.status = "Gemini не подключён: " + _classify_api_error(exc, self.model)
                    self.mode_kind = "error"
                    raise GatewayError(self.status) from None
                finally:
                    self.agent.close()
            res = validate_response(result)
            if any(s.type == "error" for s in res.steps):
                err_thought = next((s.thought for s in res.steps if s.type == "error" and s.thought), "Ошибка Gemini API")
                self.last_error = err_thought
                self.status = f"Ошибка API: {err_thought}"
                self.mode_kind = "error"
                res.meta["backend"] = "error"
                return res
            self.last_error = None
            self.status = f"Gemini подключён ({self.agent.model})"
            self.mode_kind = "gemini"
            res.meta["backend"] = "gemini"
            return res

        raise GatewayError("Gemini не подключён: укажите GEMINI_API_KEY или настройте Cloud Vertex AI.")

    def check_connection(self) -> bool:
        if not self._api_key:
            self.status = "Gemini не подключён: ключ не указан"
            return False
        from google import genai
        try:
            with genai.Client(vertexai=False, api_key=self._api_key, http_options={"timeout": 10000}) as client:
                client.models.generate_content(model=self.model, contents="Reply OK", config={"max_output_tokens": 8})
            self.status = f"Gemini подключён ({self.model})"
            self.mode_kind = "gemini"
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = _classify_api_error(exc, self.model)
            self.status = "Gemini не подключён: " + self.last_error
            self.mode_kind = "error"
            return False


class CloudBackend:
    """Connects to Vertex AI Reasoning Engine or Vertex AI Gemini endpoint."""

    def __init__(self, resource: str | None = None, project: str | None = None, location: str | None = None) -> None:
        self.resource = (
            resource
            or os.getenv("VERTEX_AGENT_RESOURCE", "")
            or os.getenv("AGENT_ENGINE_RESOURCE_NAME", "")
        ).strip()
        self.project = (project or os.getenv("GOOGLE_CLOUD_PROJECT", "")).strip()
        self.location = (location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")).strip() or "us-central1"
        self.model_location = (os.getenv("GOOGLE_CLOUD_MODEL_LOCATION", "global")).strip() or "global"
        raw_model = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
        self.model = raw_model
        self.is_demo = False
        self.last_error: str | None = None
        self.url: str | None = None

        match = re.fullmatch(
            r"projects/([a-zA-Z0-9-]+)/locations/([a-z0-9-]+)/reasoningEngines/([a-zA-Z0-9_-]+)",
            self.resource,
        )
        if match:
            region = match.group(2)
            host = "aiplatform.googleapis.com" if region == "global" else f"{region}-aiplatform.googleapis.com"
            self.url = f"https://{host}/v1/{self.resource}:query"
            self.status = f"Cloud Vertex AI Agent Engine ({match.group(1)})"
            self.mode_kind = "cloud"
        elif self.project:
            self.status = f"Cloud Vertex AI ({self.project} · {self.location})"
            self.mode_kind = "cloud"
        else:
            self.status = "Cloud Vertex AI не настроен (укажите GOOGLE_CLOUD_PROJECT или VERTEX_AGENT_RESOURCE)"
            self.mode_kind = "error"

    def query(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
        if not self.url and not self.project:
            msg = (
                "Режим Cloud Vertex AI не настроен. Укажите `GOOGLE_CLOUD_PROJECT` "
                "(и при необходимости `VERTEX_AGENT_RESOURCE`) в настройках подключения или в `.env`, "
                "а также выполните `gcloud auth application-default login`."
            )
            return validate_response({
                "answer": msg,
                "steps": [{
                    "index": 0,
                    "type": "error",
                    "thought": msg,
                    "source": "live",
                    "started_at": datetime.now(ZONE).isoformat(timespec="milliseconds"),
                    "duration_ms": 0,
                }],
                "state": copy.deepcopy(state),
                "meta": {
                    "model": self.model,
                    "session_id": f"cloud-{uuid.uuid4().hex[:8]}",
                    "total_ms": 0,
                    "tool_calls": 0,
                    "steps_count": 1,
                    "backend": "cloud-error",
                },
            })

        if self.url:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            try:
                credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                with AuthorizedSession(credentials) as session:
                    response = session.post(
                        self.url,
                        json={"classMethod": "query", "input": {"user_input": user_input, "state": copy.deepcopy(state)}},
                        timeout=(10, 90),
                        allow_redirects=False,
                    )
                if response.status_code != 200:
                    raise GatewayError(f"Ошибка Vertex AI Agent Engine (HTTP {response.status_code}). Проверьте права IAM и статус ресурса.")
                payload = response.json()
                res = validate_response(payload["output"])
                res.meta["backend"] = "cloud"
                return res
            except GatewayError as exc:
                self.status = str(exc)
                self.mode_kind = "error"
                raise
            except Exception as exc:
                msg = "Не удалось подключиться к Vertex AI Agent Engine. Проверьте учётные данные ADC (`gcloud auth application-default login`) и доступ к сети."
                self.status = msg
                self.mode_kind = "error"
                raise GatewayError(msg) from exc

        # Direct Vertex AI Gemini mode with project + location
        try:
            module = importlib.import_module("agent.artex_agent")
            cloud_agent = module.ArtexAgent(
                model=self.model,
                project=self.project,
                location=self.location,
                model_location=self.model_location,
            )
            with _QUERY_LOCK:
                try:
                    raw = cloud_agent.query(user_input=user_input, state=copy.deepcopy(state))
                finally:
                    cloud_agent.close()
            res = validate_response(raw)
            if any(s.type == "error" for s in res.steps):
                self.mode_kind = "error"
                self.status = "Ошибка запроса к Cloud Vertex AI (проверьте ADC и доступ к модели)"
                res.meta["backend"] = "cloud-error"
            else:
                res.meta["backend"] = "cloud"
            return res
        except Exception as exc:
            msg = "Ошибка вызова Cloud Vertex AI. Проверьте `GOOGLE_CLOUD_PROJECT`, права IAM и `gcloud auth application-default login`."
            self.status = msg
            self.mode_kind = "error"
            raise GatewayError(msg) from exc


class Gateway:
    def __init__(self, mode: str = "local", api_key: str | None = None, project: str | None = None, resource: str | None = None) -> None:
        if mode not in {"local", "cloud"}:
            raise GatewayError("Неизвестный режим работы.")
        self.backend = (
            CloudBackend(resource=resource, project=project)
            if mode == "cloud"
            else LocalBackend(api_key=api_key)
        )

    def query(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
        if user_input is None:
            user_input = ""
        return self.backend.query(user_input, state)


def query(user_input: str, state: dict[str, Any]) -> AgentResponse:
    return Gateway(os.getenv("ARTEX_BACKEND", "local")).query(user_input, state)
