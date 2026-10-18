"""UI gateway connecting Streamlit with local agent and Vertex AI."""

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

from agent.mcp_bridge import InMemoryMCPBridge
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
        if api_key is not None and api_key.strip():
            os.environ["GEMINI_API_KEY"] = api_key.strip()
        mode = mode or os.getenv("CAMPUSPULSE_LOCAL_MODE", "auto")
        if mode not in {"auto", "demo"}:
            mode = "auto"

        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._bridge = InMemoryMCPBridge()
        self.agent = None

        has_credentials = bool(
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
        )
        if mode == "auto" and has_credentials:
            try:
                module = importlib.import_module("agent.campuspulse_agent")
                self.agent = module.CampusPulseAgent(
                    model=self.model,
                    project=os.getenv("GOOGLE_CLOUD_PROJECT") or None,
                    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
                    model_location=os.getenv("GOOGLE_CLOUD_MODEL_LOCATION", "global"),
                )
            except Exception as exc:
                raise GatewayError("Не удалось инициализировать локального агента.") from exc

        self.status = (
            f"Подключён Gemini ({self.model})"
            if self.agent
            else "Автономный режим (MCP-инструменты)"
        )

    @property
    def is_demo(self) -> bool:
        return self.agent is None

    def query(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
        if self.agent:
            try:
                with _QUERY_LOCK:
                    result = self.agent.query(user_input=user_input, state=copy.deepcopy(state))
                res = validate_response(result)
                if not any(s.type == "error" for s in res.steps):
                    return res
            except Exception:
                pass
        return self._run_mcp_orchestrator(user_input, copy.deepcopy(state))

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
                add_step("tool_call", "live", name=name, args=args, duration_ms=0)
                tool_calls += 1
                envelope = self._bridge.call_tool(name, args)
                src = "demo" if envelope.get("source") == "demo" else "live"
                add_step(
                    "tool_result",
                    src,
                    name=name,
                    args=args,
                    result=envelope,
                    duration_ms=int(envelope.get("elapsed_ms", 1)),
                )
                return envelope

            q = user_input.strip()
            q_lower = q.casefold()
            url_match = re.search(r"https?://[^\s)\"'>]+", q)
            repo_match = re.search(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b", q)
            iso_dates = re.findall(r"\b20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b", q)

            if any(w in q_lower for w in ("репозитор", "github", "готовность", "коммит", "commit")):
                if url_match:
                    target_repo = url_match.group(0)
                elif repo_match and "/" in repo_match.group(1) and not repo_match.group(1).startswith("http"):
                    target_repo = f"https://github.com/{repo_match.group(1)}"
                else:
                    env_repo = os.getenv("GITHUB_REPOSITORY", DEFAULT_REPO).strip() or DEFAULT_REPO
                    target_repo = env_repo if env_repo.startswith("http") else f"https://github.com/{env_repo}"

                status_env = call_mcp("github_repo_status", {"repo_url": target_repo})
                expected_files = ["README.md", "requirements.txt", "agent/campuspulse_agent.py"]
                check_env = call_mcp(
                    "github_assignment_check",
                    {"repo_url": target_repo, "expected_files": expected_files},
                )

                if status_env.get("ok") and status_env.get("data"):
                    d = status_env["data"]
                    chk = check_env.get("data") or {}
                    commits = d.get("recent_commits") or []
                    commits_md = "\n".join(
                        f"- `{c.get('sha')}` — {c.get('message')} ({c.get('author')})"
                        for c in commits
                    ) or "- Нет доступных коммитов"
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
                    answer = f"Не удалось проверить репозиторий `{target_repo}`: {err}"

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
                        f"- **{c['course']}** — {c['title']} · до `{c['due_date']}` (`{c['priority']}`)"
                        for c in cands
                    )
                    answer = (
                        f"### Извлечённые дедлайны из силлабуса ({len(cands)})\n\n"
                        f"{rows}\n\n"
                        f"Задачи показаны в режиме предпросмотра. Напишите, какие из них добавить в расписание."
                    )
                else:
                    answer = "В тексте не найдено дат в формате `YYYY-MM-DD`."

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
                added = (add_env.get("data") or {}).get("added", {})
                answer = (
                    f"### Дедлайн добавлен\n\n"
                    f"- **Задача:** {added.get('title')}\n"
                    f"- **Срок сдачи:** `{added.get('due_date')}` (осталось дней: {added.get('days_left')})\n"
                    f"- **Приоритет:** `{added.get('priority')}`"
                )

            elif (
                any(w in q_lower for w in ("коворкинг", "аудитор", "кампус", "библиотек", "комната", "помещен", "корпус", "столов", "медпункт", "деканат", "фаблаб", "fablab", "где"))
                or re.search(r"c1\.[1-3]\.\d{3}", q_lower)
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
                        f"### Навигация по кампусу AITU\n\n"
                        + "\n".join(lines)
                        + "\n\nИнтерактивная схема этажей: [Открыть карту AITU](https://yuujiso.github.io/aitumap/)"
                    )
                else:
                    answer = (
                        "По вашему запросу локация не найдена в справочнике C1.1–C1.3. "
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
                    if tasks:
                        t_str = "; ".join(
                            f"**{t['course']}**: {t['title']} ({t['estimated_hours']} ч, дедлайн `{t['due_date']}`)"
                            for t in tasks
                        )
                        day_lines.append(f"- **{d['date']} ({d['weekday']})** · `{d['allocated_hours']} ч` — {t_str}")
                    else:
                        day_lines.append(f"- **{d['date']} ({d['weekday']})** · свободно (отдых или повторение тем)")

                answer = (
                    f"### Учебный план на неделю ({plan_data.get('start_date')} — {plan_data.get('end_date')})\n\n"
                    f"Запланировано задач: **{plan_data.get('total_scheduled_tasks', 0)}** · "
                    f"Общая нагрузка: **{plan_data.get('total_estimated_hours', 0)} ч**\n\n"
                    + "\n".join(day_lines)
                )

            else:
                today_env = call_mcp("get_today", {})
                dl_env = call_mcp("list_deadlines", {"days_ahead": 30})
                today_data = today_env.get("data") or {}
                deadlines = (dl_env.get("data") or {}).get("deadlines", [])

                if deadlines:
                    dl_lines = []
                    for d in deadlines:
                        days_left = d.get("days_left", 0)
                        day_label = (
                            f"просрочено на {abs(days_left)} дн."
                            if isinstance(days_left, int) and days_left < 0
                            else ("сдача сегодня" if days_left == 0 else f"осталось {days_left} дн.")
                        )
                        dl_lines.append(
                            f"- **{d.get('course', 'Курс')}** — {d.get('title')} · `{d.get('due_date')}` ({day_label}, приоритет `{d.get('priority')}`)"
                        )
                    first = deadlines[0]
                    answer = (
                        f"### Актуальные дедлайны на {today_data.get('date', '')}\n\n"
                        + "\n".join(dl_lines)
                        + f"\n\n**С чего начать:** рекомендую в первую очередь закрыть **«{first.get('title')}»** ({first.get('course')}), так как это самая приоритетная задача по срокам."
                    )
                else:
                    answer = f"На {today_data.get('date', 'сегодня')} активных дедлайнов нет."

            add_step("final", "live", thought="Ответ сформирован.", duration_ms=5)
            updated_state = self._bridge.export_state_after_query(state)
            total_ms = max(1, int((time.perf_counter_ns() - started_ns) / 1_000_000))

            return validate_response({
                "answer": answer,
                "steps": steps,
                "state": updated_state,
                "meta": {
                    "model": self.model,
                    "session_id": f"local-{uuid.uuid4().hex[:8]}",
                    "total_ms": total_ms,
                    "duration_ms": total_ms,
                    "tool_calls": tool_calls,
                    "steps_count": len(steps),
                    "backend": "local",
                },
            })


class CloudBackend:
    """Connects to Vertex AI Reasoning Engine over REST."""

    def __init__(self, resource: str | None = None) -> None:
        self.resource = (
            resource
            or os.getenv("VERTEX_AGENT_RESOURCE", "")
            or os.getenv("AGENT_ENGINE_RESOURCE_NAME", "")
        )
        match = re.fullmatch(
            r"projects/([a-zA-Z0-9-]+)/locations/([a-z0-9-]+)/reasoningEngines/([a-zA-Z0-9_-]+)",
            self.resource,
        )
        if not match:
            raise GatewayError(
                "Укажите VERTEX_AGENT_RESOURCE в .env (projects/PROJECT/locations/REGION/reasoningEngines/ID)."
            )
        region = match.group(2)
        host = "aiplatform.googleapis.com" if region == "global" else f"{region}-aiplatform.googleapis.com"
        self.url = f"https://{host}/v1/{self.resource}:query"
        self.status = "Vertex AI Agent Engine"
        self.is_demo = False

    def query(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
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
                raise GatewayError(f"Ошибка Vertex AI (HTTP {response.status_code}). Проверьте доступ и статус деплоя.")
            payload = response.json()
            return validate_response(payload["output"])
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError("Не удалось выполнить запрос к облачному агенту.") from exc


class Gateway:
    def __init__(self, mode: str = "local", api_key: str | None = None) -> None:
        if mode not in {"local", "cloud"}:
            raise GatewayError("Неизвестный режим работы.")
        self.backend = CloudBackend() if mode == "cloud" else LocalBackend(api_key=api_key)

    def query(self, user_input: str, state: dict[str, Any]) -> AgentResponse:
        if not user_input.strip() or len(user_input) > 10000:
            raise GatewayError("Введите запрос длиной от 1 до 10 000 символов.")
        return self.backend.query(user_input, state)


def query(user_input: str, state: dict[str, Any]) -> AgentResponse:
    return Gateway(os.getenv("CAMPUSPULSE_BACKEND", "local")).query(user_input, state)
