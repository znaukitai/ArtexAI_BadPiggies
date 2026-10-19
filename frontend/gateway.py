"""UI gateway connecting Streamlit with local agent, MCP orchestrator, and Vertex AI."""

from __future__ import annotations

import copy
import importlib
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
ZONE = ZoneInfo("Asia/Almaty")
DEFAULT_REPO = "znaukitai/CampusPulseAI_BadPiggies"
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

from agent.campuspulse_agent import is_unrecognized_or_offtopic, _classify_api_error
from core.input_normalization import normalize_room_query, normalize_api_key, is_greeting, GREETING
from agent.mcp_bridge import InMemoryMCPBridge
from agent.prompts import UNRECOGNIZED_QUERY_MESSAGE
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
    """Runs Gemini agent when API key is configured, otherwise runs local MCP tool orchestrator."""

    def __init__(self, mode: str | None = None, api_key: str | None = None) -> None:
        # Never mutate os.environ with user-entered key; keep in instance memory only
        self._api_key = normalize_api_key(api_key) or normalize_api_key(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        mode = mode or os.getenv("CAMPUSPULSE_LOCAL_MODE", "auto")
        if mode not in {"auto", "demo"}:
            mode = "auto"

        raw_model = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
        self.model = raw_model
        self._bridge = InMemoryMCPBridge()
        self.agent = None
        self.last_error: str | None = None

        has_credentials = bool(self._api_key)
        if mode == "auto" and has_credentials:
            try:
                module = importlib.import_module("agent.campuspulse_agent")
                self.agent = module.CampusPulseAgent(
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
            self.status = "Встроенный режим (без LLM)" if mode == "demo" else "Gemini не подключён: ключ не указан"
            self.mode_kind = "orchestrator"

    @property
    def is_demo(self) -> bool:
        return self.agent is None

    def query(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
        if is_unrecognized_or_offtopic(user_input):
            return validate_response({
                "answer": GREETING if is_greeting(user_input) else UNRECOGNIZED_QUERY_MESSAGE,
                "steps": [],
                "state": copy.deepcopy(state),
                "meta": {
                    "model": self.model if self.agent else "Встроенный оркестратор MCP",
                    "session_id": f"local-{uuid.uuid4().hex[:8]}",
                    "total_ms": 0,
                    "duration_ms": 0,
                    "tool_calls": 0,
                    "steps_count": 0,
                    "backend": "gemini" if self.agent else "orchestrator",
                },
            })

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

        return self._run_mcp_orchestrator(user_input, copy.deepcopy(state))

    def check_connection(self) -> bool:
        if not self._api_key:
            self.status = "Gemini не подключён: ключ не указан"
            return False
        from google import genai
        try:
            with genai.Client(api_key=self._api_key, http_options={"timeout": 10000}) as client:
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

    def _run_mcp_orchestrator(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
        started_ns = time.perf_counter_ns()
        state.setdefault("deadlines", get_default_deadlines())
        with _QUERY_LOCK:
            self._bridge.sync_state_before_query(state)

            steps: list[dict[str, Any]] = []
            tool_calls = 0

            def add_step(kind: str, source: str = "live", **fields: Any) -> None:
                steps.append({
                    "index": len(steps),
                    "type": kind,
                    "source": source,
                    "started_at": datetime.now(ZONE).isoformat(timespec="milliseconds"),
                    **fields,
                })

            def call_mcp(name: str, args: dict[str, Any]) -> dict[str, Any]:
                nonlocal tool_calls
                envelope = self._bridge.call_tool(name, args)
                src = "demo" if envelope.get("source") == "demo" else "live"
                add_step("tool_call", src, name=name, args=args, duration_ms=0)
                tool_calls += 1
                add_step(
                    "tool_result",
                    src,
                    name=name,
                    args=args,
                    result=envelope,
                    duration_ms=int(envelope.get("elapsed_ms", 1)),
                )
                return envelope

            q = normalize_room_query(user_input.strip())
            q_lower = q.casefold()
            url_match = re.search(r"https?://[^\s)\"'>]+", q)
            repo_match = re.search(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?![A-Za-z0-9_.-])", q)
            iso_dates = re.findall(r"\b20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b", q)

            if any(w in q_lower for w in ("репозитор", "github", "гитхаб", "готовность", "коммит", "commit")) or url_match:
                if url_match:
                    target_repo = url_match.group(0)
                elif repo_match and not repo_match.group(1).lower().startswith(("c1.", "http")):
                    target_repo = f"https://github.com/{repo_match.group(1)}"
                else:
                    env_repo = os.getenv("GITHUB_REPOSITORY", DEFAULT_REPO).strip() or DEFAULT_REPO
                    target_repo = env_repo if env_repo.startswith("http") else f"https://github.com/{env_repo}"

                status_env = call_mcp("github_repo_status", {"repo_url": target_repo})
                if status_env.get("ok") and status_env.get("data"):
                    expected_files = ["README.md", "requirements.txt", "agent/campuspulse_agent.py"]
                    check_env = call_mcp(
                        "github_assignment_check",
                        {"repo_url": target_repo, "expected_files": expected_files},
                    )
                    d = status_env["data"]
                    chk = check_env.get("data") or {}
                    commits = d.get("recent_commits") or []
                    commits_md = "\n".join(
                        f"- `{c.get('sha')}` — {c.get('message')} ({c.get('author')})"
                        for c in commits
                    ) or "- Коммиты отсутствуют (пустой репозиторий)"
                    found_str = ", ".join(f"`{f}`" for f in chk.get("found_files", [])) or "нет"
                    missing_str = ", ".join(f"`{f}`" for f in chk.get("missing_files", [])) or "нет"
                    ready_badge = "Готов к проверке" if chk.get("ready_for_submission") else "Требуется доработка"

                    answer = (
                        f"### Проверка репозитория [{d.get('full_name')}]({d.get('html_url')})\n\n"
                        f"- **Ветка по умолчанию:** `{d.get('default_branch')}` · **Язык:** `{d.get('language') or 'Python'}`\n"
                        f"- **Статус файлов:** `{chk.get('completeness_pct', 0)}%` ({ready_badge})\n"
                        f"- **Найдены:** {found_str}\n"
                        f"- **Отсутствуют:** {missing_str}\n\n"
                        f"**Последние коммиты:**\n{commits_md}"
                    )
                else:
                    err = status_env.get("error") or "Не удалось получить статус репозитория."
                    answer = f"Не удалось проверить репозиторий: {err}"

            elif ("силлабус" in q_lower or "syllabus" in q_lower or "извлек" in q_lower) or (
                len(iso_dates) >= 2 and "добав" not in q_lower
            ):
                sample_text = q
                if not iso_dates:
                    syllabus_path = ROOT / "data" / "sample_syllabus.txt"
                    if syllabus_path.exists():
                        sample_text = syllabus_path.read_text(encoding="utf-8")
                parsed_env = call_mcp("parse_syllabus_text", {"text": sample_text})
                cands = (parsed_env.get("data") or {}).get("candidates", [])
                if cands:
                    rows = "\n".join(
                        f"- **{c['course']}** — {c['title']} · до **{format_date_ru(c['due_date'])}** (приоритет: {format_priority_ru(c['priority'])})"
                        for c in cands
                    )
                    answer = (
                        f"### Извлечённые дедлайны из силлабуса ({len(cands)})\n\n"
                        f"{rows}\n\n"
                        f"Задачи показаны в режиме предпросмотра. Напишите, какие из них добавить в расписание."
                    )
                else:
                    answer = "В тексте не найдено дат в формате `ГГГГ-ММ-ДД`."

            elif "добав" in q_lower and ("дедлайн" in q_lower or "задач" in q_lower or iso_dates):
                today_env = call_mcp("get_today", {})
                today_str = (today_env.get("data") or {}).get("date", str(datetime.now(ZONE).date()))
                due = iso_dates[0] if iso_dates else str(datetime.fromisoformat(today_str).date() + timedelta(days=5))
                prio = "critical" if "крит" in q_lower else ("high" if "высок" in q_lower else "medium")
                clean_title = re.sub(r"\b(добавь|добавить|дедлайн|задачу|по курсу|до)\b", "", q, flags=re.IGNORECASE)
                for dt in iso_dates:
                    clean_title = clean_title.replace(dt, "")
                clean_title = clean_title.strip(" -–—,:;.") or "Новая учебная задача"
                add_env = call_mcp(
                    "add_deadline",
                    {
                        "course": "Учебный курс",
                        "title": clean_title[:80],
                        "due_date": due,
                        "priority": prio,
                    },
                )
                if add_env.get("ok") and add_env.get("data"):
                    added = add_env["data"].get("added", {})
                    days_val = int(added.get("days_left", 0))
                    answer = (
                        f"### Дедлайн добавлен\n\n"
                        f"- **Задача:** {added.get('title')}\n"
                        f"- **Срок сдачи:** {format_date_ru(added.get('due_date', ''))} ({format_days_left_ru(days_val)})\n"
                        f"- **Приоритет:** {format_priority_ru(added.get('priority', 'medium'))}"
                    )
                else:
                    answer = f"Не удалось добавить дедлайн: {add_env.get('error', 'ошибка формата даты')}"

            elif (
                any(w in q_lower for w in ("коворкинг", "аудитор", "кампус", "библиотек", "комната", "помещен", "кабинет", "корпус", "столов", "медпункт", "деканат", "фаблаб", "fablab", "регистратор", "цон"))
                or re.search(r"c1\.(?:[1-3]\.)?\d{3}", q_lower)
            ):
                loc_env = call_mcp("find_campus_place", {"query": q})
                data = loc_env.get("data") or {}
                matches = data.get("locations", [])
                if matches:
                    lines = []
                    for loc in matches[:8]:
                        name = loc.get("name") or loc.get("code")
                        code = loc.get("code", "")
                        block = loc.get("block", "")
                        floor = loc.get("floor", "")
                        desc = f" — {loc['description']}" if loc.get("description") else ""
                        hours = f" ({loc['hours']})" if loc.get("hours") else ""
                        if code and not str(code).startswith("facility:") and code not in str(name):
                            lines.append(f"- **{code}** · {name} — блок `{block}`, этаж `{floor}`{hours}{desc}")
                        else:
                            lines.append(f"- **{name}** — блок `{block}`, этаж `{floor}`{hours}{desc}")
                    answer = (
                        f"### Навигация по кампусу AITU (DEMO · справочник)\n\n"
                        + "\n".join(lines)
                        + "\n\nИнтерактивная схема этажей: [Открыть карту AITU](https://yuujiso.github.io/aitumap/)"
                    )
                else:
                    answer = (
                        "Такой аудитории нет в справочнике C1.1–C1.3 (DEMO). "
                        + "Похожие варианты: " + ", ".join(data.get("suggestions", [])) + ". "
                        +
                        "Попробуйте указать код кабинета (например, `C1.2.223`) или откройте [карту кампуса](https://yuujiso.github.io/aitumap/)."
                    )

            elif any(w in q_lower for w in ("план", "сбалансирован", "расписан")):
                today_env = call_mcp("get_today", {})
                today_str = (today_env.get("data") or {}).get("date", str(datetime.now(ZONE).date()))
                plan_env = call_mcp("plan_week", {"start_date": today_str})
                plan_data = plan_env.get("data") or {}
                day_lines = []
                for d in plan_data.get("days", []):
                    tasks = d.get("tasks", [])
                    wd_ru = WEEKDAY_RU.get(d.get("weekday", ""), d.get("weekday", ""))
                    date_ru = format_date_ru(d.get("date", ""))
                    if tasks:
                        t_str = "; ".join(
                            f"**{t['course']}**: {t['title']} ({t['estimated_hours']} ч, срок {format_date_ru(t['due_date'])}, приоритет: {format_priority_ru(t.get('priority', 'medium'))})"
                            for t in tasks
                        )
                        day_lines.append(f"- **{date_ru} ({wd_ru})** · {d['allocated_hours']} ч — {t_str}")
                    else:
                        day_lines.append(f"- **{date_ru} ({wd_ru})** · свободно (отдых или повторение тем)")

                start_ru = format_date_ru(plan_data.get("start_date", ""))
                end_ru = format_date_ru(plan_data.get("end_date", ""))
                answer = (
                    f"### Учебный план на неделю ({start_ru} — {end_ru})\n\n"
                    f"Запланировано задач: **{plan_data.get('total_scheduled_tasks', 0)}** · "
                    f"Общая нагрузка: **{plan_data.get('total_estimated_hours', 0)} ч**\n\n"
                    + "\n".join(day_lines)
                )

            elif any(w in q_lower for w in ("горит", "дедлайн", "deadline", "срок", "сдач", "задач", "начать", "недел", "сегодня", "завтра", "число", "дата", "курс", "лаб", "экзамен")):
                today_env = call_mcp("get_today", {})
                dl_env = call_mcp("list_deadlines", {"days_ahead": 30})
                today_data = today_env.get("data") or {}
                deadlines = (dl_env.get("data") or {}).get("deadlines", [])
                today_ru = format_date_ru(today_data.get("date", ""), with_year=True)

                if deadlines:
                    dl_lines = []
                    for d in deadlines:
                        days_left = int(d.get("days_left", 0))
                        day_label = format_days_left_ru(days_left)
                        due_ru = format_date_ru(d.get("due_date", ""))
                        prio_ru = format_priority_ru(d.get("priority", "medium"))
                        demo_tag = " `[DEMO]`" if d.get("source", "demo") == "demo" else ""
                        dl_lines.append(
                            f"- **{d.get('course', 'Курс')}** — {d.get('title')} · {due_ru} ({day_label}, приоритет: {prio_ru}){demo_tag}"
                        )
                    first = deadlines[0]
                    answer = (
                        f"### Актуальные дедлайны на {today_ru}\n\n"
                        + "\n".join(dl_lines)
                        + f"\n\n**С чего начать:** рекомендую в первую очередь закрыть **«{first.get('title')}»** ({first.get('course')}), так как это самая приоритетная задача по срокам."
                    )
                else:
                    answer = f"На {today_ru} активных дедлайнов нет."

            else:
                return validate_response({
                    "answer": GREETING if is_greeting(user_input) else UNRECOGNIZED_QUERY_MESSAGE,
                    "steps": [],
                    "state": self._bridge.export_state_after_query(state),
                    "meta": {
                        "model": "Встроенный оркестратор MCP",
                        "session_id": f"local-{uuid.uuid4().hex[:8]}",
                        "total_ms": 0,
                        "duration_ms": 0,
                        "tool_calls": 0,
                        "steps_count": 0,
                        "backend": "orchestrator",
                    },
                })

            add_step("final", "live", thought="Ответ сформирован.", duration_ms=5)
            updated_state = self._bridge.export_state_after_query(state)
            total_ms = max(1, int((time.perf_counter_ns() - started_ns) / 1_000_000))

            return validate_response({
                "answer": answer,
                "steps": steps,
                "state": updated_state,
                "meta": {
                    "model": "Встроенный оркестратор MCP",
                    "session_id": f"local-{uuid.uuid4().hex[:8]}",
                    "total_ms": total_ms,
                    "duration_ms": total_ms,
                    "tool_calls": tool_calls,
                    "steps_count": len(steps),
                    "backend": "orchestrator",
                },
            })


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
        self.model = DEFAULT_MODEL if raw_model == "gemini-2.5-flash" else raw_model
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
        if is_unrecognized_or_offtopic(user_input):
            return validate_response({
                "answer": GREETING if is_greeting(user_input) else UNRECOGNIZED_QUERY_MESSAGE,
                "steps": [],
                "state": copy.deepcopy(state),
                "meta": {
                    "model": self.model,
                    "session_id": f"cloud-{uuid.uuid4().hex[:8]}",
                    "total_ms": 0,
                    "tool_calls": 0,
                    "steps_count": 0,
                    "backend": "cloud",
                },
            })

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
            module = importlib.import_module("agent.campuspulse_agent")
            cloud_agent = module.CampusPulseAgent(
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
        if len(str(user_input)) > 10000:
            return validate_response({
                "answer": GREETING if is_greeting(user_input) else UNRECOGNIZED_QUERY_MESSAGE,
                "steps": [],
                "state": copy.deepcopy(state),
                "meta": {
                    "model": getattr(self.backend, "model", DEFAULT_MODEL),
                    "session_id": f"sess-{uuid.uuid4().hex[:8]}",
                    "total_ms": 0,
                    "tool_calls": 0,
                    "steps_count": 0,
                    "backend": getattr(self.backend, "mode_kind", "local"),
                },
            })
        return self.backend.query(user_input, state)


def query(user_input: str, state: dict[str, Any]) -> AgentResponse:
    return Gateway(os.getenv("CAMPUSPULSE_BACKEND", "local")).query(user_input, state)
