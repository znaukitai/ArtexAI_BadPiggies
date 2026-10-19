"""UI components for Artex AI: deadline cards, LIVE/DEMO badge, agent step trace, empty/loading/error states."""

from __future__ import annotations

import html
import json
import os
from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st

from core.deadline_logic import (
    calculate_urgency,
    complete_deadline,
    delete_deadline,
    format_date_ru,
    format_days_left_ru,
    format_priority_ru,
    format_urgency_ru,
    group_deadlines_by_horizon,
)
from frontend.gateway import ZONE, GatewayError
from frontend.icons import get_avatar_uri, get_icon, icon
from frontend.theme import PALETTES, apply_theme, inject_theme


def _render_html(markup: str) -> None:
    """Render single-line HTML safely without CommonMark indented code-block misparsing."""
    clean = " ".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(clean, unsafe_allow_html=True)


def format_badge_html(source: str | None) -> str:
    """Render semantic LIVE or DEMO pill badge HTML (green only for LIVE, orange only for DEMO)."""
    src = (source or "").strip().lower()
    if src == "live":
        return '<span class="mode-pill mode-live"><span class="mode-dot"></span>LIVE</span>'
    return '<span class="mode-pill mode-demo"><span class="mode-dot"></span>DEMO</span>'


def render_mode_badge(is_live: bool, label: str | None = None) -> str:
    """Return HTML string for LIVE or DEMO pill badge with CSS dot."""
    cls = "mode-live" if is_live else "mode-demo"
    text = html.escape(label or ("LIVE" if is_live else "DEMO"))
    return f'<span class="mode-pill {cls}"><span class="mode-dot"></span>{text}</span>'


def render_empty_state() -> None:
    """Render empty chat state with signature pulse emblem and single-line subtitle."""
    logo_svg = icon("logo", size=26)
    _render_html(
        f'<div class="hero-box">'
        f'<div class="hero-logo-badge">{logo_svg}</div>'
        f'<div class="hero-title">Чем помочь по учёбе сегодня?</div>'
        f'<div class="hero-sub">Дедлайны AITU, проверка GitHub, расписание на неделю и карта корпусов C1</div>'
        f"</div>"
    )


def render_loading_state(text: str = "Анализирую запрос и проверяю инструменты...") -> None:
    """Render subtle pulse loading indicator without fake percentages."""
    loader_svg = icon("loader", size=18)
    safe_text = html.escape(text)
    _render_html(
        f'<div class="cp-loading-card">'
        f'<span class="cp-loading-icon">{loader_svg}</span>'
        f"<span>{safe_text}</span>"
        f"</div>"
    )


def render_error_card(error_text: str, retry_key: str, on_retry_prompt: str | None = None) -> bool:
    """Render clean error card with warning icon, clear message, and 'Повторить' button."""
    warn_svg = icon("warning", size=20)
    first_line = (error_text or "Не удалось выполнить запрос к агенту.").strip().splitlines()[0]
    safe_msg = html.escape(first_line)
    _render_html(
        f'<div class="cp-error-card">'
        f'<span class="cp-error-icon">{warn_svg}</span>'
        f'<div><div class="cp-error-title">Не удалось получить ответ</div>'
        f'<div class="cp-error-desc">{safe_msg}</div></div>'
        f"</div>"
    )
    if on_retry_prompt:
        if st.button("Повторить", icon=":material/refresh:", key=retry_key):
            return True
    return False


_GROUP_LABELS_RU = [
    ("overdue", "Просрочено"),
    ("today", "Сегодня"),
    ("this_week", "На этой неделе"),
    ("later", "Позже"),
]


def _urgency_visuals(urg_code: str, priority: str) -> tuple[str, str, str]:
    """Return (card_class, chip_class, icon_name) for deadline urgency scale."""
    prio = priority.strip().lower()
    if urg_code in {"overdue", "today"} or prio == "critical":
        return ("dl-critical", "chip-critical", "warning")
    if urg_code == "urgent" or prio == "high":
        return ("dl-high", "chip-high", "clock")
    return ("dl-normal", "chip-normal", "calendar")


def _render_single_deadline_card(
    task: dict[str, Any],
    today: date,
    state: dict[str, Any],
    workspace: dict[str, Any] | None = None,
) -> None:
    """Render one deadline card with left urgency stripe and clean action buttons."""
    from mcp_servers.academic_schedule import set_deadline_store

    task_id = str(task.get("id", ""))
    raw_title = str(task.get("title", "Без названия"))
    raw_course = str(task.get("course", "Курс"))
    raw_due = str(task.get("due_date") or task.get("due") or "—")
    raw_prio = str(task.get("priority", "medium"))

    title = html.escape(raw_title)
    course = html.escape(raw_course)
    due_str = html.escape(format_date_ru(raw_due))
    prio_ru = html.escape(format_priority_ru(raw_prio))

    try:
        delta, urg_code = calculate_urgency(raw_due, today)
        urg_ru = format_urgency_ru(urg_code)
        days_ru = format_days_left_ru(delta)
        card_cls, chip_cls, chip_icon_name = _urgency_visuals(urg_code, raw_prio)
        urg_svg = icon(chip_icon_name, size=13)
        chip_label = html.escape(f"{urg_ru} · {days_ru}")
        chip_html = f'<span class="dl-chip {chip_cls}">{urg_svg}<span>{chip_label}</span></span>'
    except ValueError:
        card_cls = "dl-normal"
        chip_html = '<span class="dl-chip chip-normal">—</span>'

    cal_svg = icon("calendar_clock", size=14)
    card_markup = (
        f'<div class="dl-card {card_cls}">'
        f'<div class="dl-course" title="{course}">{course}</div>'
        f'<div class="dl-title" title="{title}">{title}</div>'
        f'<div class="dl-footer">'
        f'<span class="dl-date">{cal_svg}<span>{due_str} · {prio_ru}</span></span>'
        f"{chip_html}"
        f"</div>"
        f"</div>"
    )
    _render_html(card_markup)

    confirm_key = f"confirm_del_{task_id}"
    if st.session_state.get(confirm_key):
        st.caption("Удалить эту задачу?")
        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button("Да, удалить", key=f"del_yes_{task_id}", use_container_width=True):
                updated, _ = delete_deadline(state.get("deadlines", []), task_id)
                state["deadlines"] = updated
                set_deadline_store(updated)
                st.session_state.pop(confirm_key, None)
                st.rerun()
        with c_no:
            if st.button("Отмена", key=f"del_no_{task_id}", use_container_width=True):
                st.session_state.pop(confirm_key, None)
                st.rerun()
    else:
        c_done, c_ask, c_del = st.columns(3)
        with c_done:
            if st.button(
                "Готово",
                key=f"done_{task_id}",
                help="Отметить задачу выполненной",
                use_container_width=True,
            ):
                updated, _ = complete_deadline(state.get("deadlines", []), task_id)
                state["deadlines"] = updated
                set_deadline_store(updated)
                st.rerun()
        with c_ask:
            if st.button(
                "В чат",
                key=f"ask_{task_id}",
                help="Спросить агента, с чего начать по этой задаче",
                use_container_width=True,
            ):
                ask_prompt = f"С чего начать по задаче «{raw_title}» ({raw_course})?"
                if workspace is not None and "gateway" in workspace:
                    workspace["messages"].append({"role": "user", "content": ask_prompt})
                    try:
                        res = workspace["gateway"].query(ask_prompt, workspace["state"]).model_dump(mode="json")
                        workspace["state"] = res["state"]
                        workspace["messages"].append({"role": "assistant", "response": res})
                    except GatewayError as exc:
                        workspace["messages"].append(
                            {"role": "assistant", "content": str(exc), "failed_prompt": ask_prompt}
                        )
                else:
                    st.session_state["chat_input_box"] = ask_prompt
                st.rerun()
        with c_del:
            if st.button(
                "Удалить",
                key=f"del_{task_id}",
                help="Удалить задачу",
                use_container_width=True,
            ):
                st.session_state[confirm_key] = True
                st.rerun()


def render_deadlines(
    state: dict[str, Any],
    workspace: dict[str, Any] | None = None,
) -> None:
    """Render smart grouped deadline panel in the sidebar without raw HTML leaks."""
    deadlines = state.get("deadlines", [])
    if not isinstance(deadlines, list):
        return

    today = datetime.now(ZONE).date()
    groups = group_deadlines_by_horizon(deadlines, today)
    total_active = sum(len(items) for items in groups.values())

    if total_active == 0:
        check_svg = icon("check", size=16)
        _render_html(
            f'<div class="dl-card dl-normal" style="display:flex;align-items:center;justify-content:center;gap:8px;color:var(--cp-muted);padding:14px;">'
            f'<span style="color:var(--cp-accent);display:inline-flex;">{check_svg}</span>'
            f"<span>Дедлайнов пока нет</span></div>"
        )
        col_l, col_c, col_r = st.columns([2, 1, 2])
        with col_c:
            if st.button("", icon=":material/add:", key="empty_plus_btn", help="Добавить дедлайн"):
                if workspace is not None:
                    open_action_dialog(workspace, "Добавить дедлайн")
        return

    for group_key, group_title_ru in _GROUP_LABELS_RU:
        items = groups.get(group_key, [])
        if not items:
            continue
        header_label = f"{group_title_ru} ({len(items)})"
        if group_key == "later":
            with st.expander(header_label, expanded=False):
                for task in items:
                    _render_single_deadline_card(task, today, state, workspace=workspace)
        else:
            _render_html(
                f'<div style="font-size:12px;font-weight:600;color:var(--cp-muted);text-transform:uppercase;letter-spacing:0.05em;margin:12px 0 6px 0;font-variant-numeric:tabular-nums;">{html.escape(header_label)}</div>'
            )
            for task in items:
                _render_single_deadline_card(task, today, state, workspace=workspace)


_STEP_TYPE_LABELS = {
    "thought": "Размышление",
    "tool_call": "Вызов инструмента",
    "tool_result": "Результат инструмента",
    "final": "Формирование ответа",
    "error": "Ошибка",
}

_STEP_TYPE_ICONS = {
    "thought": "logo",
    "tool_call": "wrench",
    "tool_result": "braces",
    "final": "check",
    "error": "warning",
}


def render_response(response: dict[str, Any]) -> None:
    """Render assistant message and collapsible execution trace with LIVE/DEMO badges."""
    raw_answer = str(response.get("answer", ""))
    formatted_answer = (
        raw_answer.replace("`[DEMO]`", format_badge_html("demo"))
        .replace("`[LIVE]`", format_badge_html("live"))
    )
    st.markdown(formatted_answer, unsafe_allow_html=True)

    steps = response.get("steps") or []
    meta = response.get("meta") or {}
    if not isinstance(steps, list) or not steps:
        return

    backend = str(meta.get("backend", "local-orchestrator"))
    model_name = html.escape(str(meta.get("model", "mcp-orchestrator")))
    total_ms = int(meta.get("total_ms", 0) or 0)
    tool_calls_count = int(meta.get("tool_calls", 0) or 0)

    is_live = backend in {"local", "cloud"} and not any(
        isinstance(s, dict) and s.get("type") == "error" for s in steps
    )
    overall_badge = format_badge_html("live" if is_live else "demo")

    with st.expander("Как агент пришёл к ответу", icon=":material/account_tree:", expanded=False):
        _render_html(
            f'<div class="trace-header-row">'
            f'<div style="display:inline-flex;align-items:center;gap:10px;flex-wrap:wrap;">'
            f"{overall_badge}"
            f"<span>Модель: <strong style=\"color:var(--cp-text);\">{model_name}</strong></span>"
            f"</div>"
            f'<div style="display:inline-flex;align-items:center;gap:12px;font-variant-numeric:tabular-nums;">'
            f"<span>Вызовов MCP: <strong style=\"color:var(--cp-text);\">{tool_calls_count}</strong></span>"
            f"<span>Время: <strong style=\"color:var(--cp-text);\">{total_ms} мс</strong></span>"
            f"</div>"
            f"</div>"
        )

        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            stype = str(step.get("type", "thought"))
            type_label = html.escape(_STEP_TYPE_LABELS.get(stype, stype))
            step_icon_name = _STEP_TYPE_ICONS.get(stype, "info")
            step_svg = icon(step_icon_name, size=15)

            tool_name = step.get("name")
            tool_html = (
                f'<span style="font-family:var(--cp-font-mono);color:var(--cp-accent);margin-left:4px;">{html.escape(str(tool_name))}</span>'
                if tool_name
                else ""
            )
            dur = step.get("duration_ms")
            dur_html = f"<span>{int(dur)} мс</span>" if dur is not None else ""

            src = str(step.get("source") or "").strip().lower()
            step_badge = format_badge_html("live" if src == "live" else "demo") if src in {"live", "demo"} else ""

            thought_html = ""
            if step.get("thought"):
                thought_html = (
                    f'<div style="font-size:13.5px;color:var(--cp-muted);margin-top:6px;">'
                    f'{html.escape(str(step["thought"]))}</div>'
                )

            details_parts: list[str] = []
            if step.get("args") is not None:
                args_json = html.escape(json.dumps(step["args"], ensure_ascii=False, indent=2))
                braces_svg = icon("braces", size=13)
                details_parts.append(
                    f'<details style="margin-top:6px;"><summary style="cursor:pointer;font-size:12.5px;color:var(--cp-muted);display:inline-flex;align-items:center;gap:5px;">'
                    f'{braces_svg}<span>Аргументы вызова</span></summary>'
                    f'<pre style="margin-top:6px;padding:8px 10px;font-size:12px;overflow-x:auto;"><code>{args_json}</code></pre></details>'
                )
            if step.get("result") is not None:
                res_json = html.escape(json.dumps(step["result"], ensure_ascii=False, indent=2))
                braces_svg = icon("braces", size=13)
                details_parts.append(
                    f'<details style="margin-top:6px;"><summary style="cursor:pointer;font-size:12.5px;color:var(--cp-muted);display:inline-flex;align-items:center;gap:5px;">'
                    f'{braces_svg}<span>Результат JSON</span></summary>'
                    f'<pre style="margin-top:6px;padding:8px 10px;font-size:12px;overflow-x:auto;"><code>{res_json}</code></pre></details>'
                )

            _render_html(
                f'<div class="trace-step-card">'
                f'<div class="trace-step-top">'
                f'<span class="trace-step-name">'
                f'<span style="color:var(--cp-accent);display:inline-flex;">{step_svg}</span>'
                f"<span>#{idx} {type_label}</span>"
                f"{tool_html}"
                f"</span>"
                f'<span class="trace-step-meta">{dur_html}{step_badge}</span>'
                f"</div>"
                f"{thought_html}"
                f'{"".join(details_parts)}'
                f"</div>"
            )


_PRIORITY_OPTIONS_RU_TO_EN = {
    "Критично": "critical",
    "Высокий": "high",
    "Средний": "medium",
    "Низкий": "low",
}


@st.dialog("Быстрые действия", width="large")
def open_action_dialog(workspace: dict[str, Any], initial_action: str = "Добавить дедлайн") -> None:
    """Modal dialog providing 5 quick actions backed by MCP tools."""
    from mcp_servers.academic_schedule import (
        add_deadline,
        get_deadline_store,
        parse_syllabus_text,
        set_deadline_store,
    )

    actions = [
        "Добавить дедлайн",
        "Загрузить силлабус",
        "План на неделю",
        "Проверить репозиторий",
        "Найти аудиторию",
    ]
    default_idx = actions.index(initial_action) if initial_action in actions else 0
    chosen = st.radio(
        "Выберите действие",
        actions,
        index=default_idx,
        horizontal=True,
        key="action_dialog_choice",
    )
    today = datetime.now(ZONE).date()

    if chosen == "Добавить дедлайн":
        with st.form("add_deadline_form", clear_on_submit=False):
            course = st.text_input(
                "Курс",
                value="AI & LLM Engineering",
                placeholder="Например: CS301 Distributed Systems",
            )
            title = st.text_input("Название задачи", placeholder="Например: Лабораторная работа №5")
            col_d, col_p = st.columns(2)
            with col_d:
                due_val = st.date_input("Срок сдачи", value=today + timedelta(days=3))
            with col_p:
                prio_label = st.selectbox("Приоритет", list(_PRIORITY_OPTIONS_RU_TO_EN.keys()), index=1)
            submitted = st.form_submit_button("Добавить в дедлайны", use_container_width=True)

        if submitted:
            if not title.strip():
                st.error("Укажите название задачи.")
            else:
                set_deadline_store(workspace["state"].get("deadlines", []))
                res = add_deadline(
                    course=course.strip() or "Общий курс",
                    title=title.strip(),
                    due_date=due_val.isoformat(),
                    priority=_PRIORITY_OPTIONS_RU_TO_EN[prio_label],  # type: ignore[arg-type]
                )
                if res.get("ok"):
                    workspace["state"]["deadlines"] = get_deadline_store()
                    added = res["data"]["added"]
                    days_ru = format_days_left_ru(int(added.get("days_left", 0)))
                    due_ru = format_date_ru(added.get("due_date", ""))
                    prio_ru = format_priority_ru(added.get("priority", "medium"))
                    msg = (
                        f"### Дедлайн добавлен\n\n"
                        f"- **Курс:** {added.get('course')}\n"
                        f"- **Задача:** {added.get('title')}\n"
                        f"- **Срок сдачи:** {due_ru} ({days_ru})\n"
                        f"- **Приоритет:** {prio_ru}"
                    )
                    workspace["messages"].append(
                        {
                            "role": "assistant",
                            "response": {"answer": msg, "steps": [], "meta": {"backend": "local"}},
                        }
                    )
                    st.rerun()
                else:
                    st.error(res.get("error") or "Не удалось добавить дедлайн.")

    elif chosen == "Загрузить силлабус":
        st.caption("Вставьте текст силлабуса с датами в формате ГГГГ-ММ-ДД или загрузите текстовый файл.")
        uploaded = st.file_uploader("Текстовый файл силлабуса (.txt, .md)", type=["txt", "md"])
        default_syllabus = ""
        if uploaded is not None:
            try:
                default_syllabus = uploaded.getvalue().decode("utf-8", errors="replace")
            except Exception:
                default_syllabus = ""

        raw_text = st.text_area(
            "Текст силлабуса",
            value=default_syllabus
            or "CS301 - Lab 5 Raft Replication due 2026-10-24 [high]\nAI & LLM - Final Project Demo due 2026-10-29 [critical]",
            height=130,
        )
        if st.button("Распознать дедлайны", key="parse_syllabus_btn", use_container_width=True):
            parsed = parse_syllabus_text(raw_text)
            if parsed.get("ok"):
                st.session_state.syllabus_candidates = parsed["data"].get("candidates", [])
            else:
                st.error(parsed.get("error") or "Ошибка разбора силлабуса.")

        candidates = st.session_state.get("syllabus_candidates", [])
        if candidates:
            st.markdown(f"**Найдено задач: {len(candidates)}** (отметьте нужные для сохранения):")
            selected_items: list[dict[str, Any]] = []
            for idx, cand in enumerate(candidates):
                c_course = cand.get("course", "Курс")
                c_title = cand.get("title", "Задача")
                c_due = format_date_ru(cand.get("due_date", ""), with_year=True)
                c_prio = format_priority_ru(cand.get("priority", "medium"))
                checked = st.checkbox(
                    f"{c_course} — {c_title} · {c_due} ({c_prio})",
                    value=True,
                    key=f"syl_cand_{idx}",
                )
                if checked:
                    selected_items.append(cand)

            if st.button("Добавить выбранные", key="save_syllabus_btn", use_container_width=True):
                if not selected_items:
                    st.warning("Выберите хотя бы одну задачу.")
                else:
                    set_deadline_store(workspace["state"].get("deadlines", []))
                    added_count = 0
                    for item in selected_items:
                        r = add_deadline(
                            course=str(item.get("course", "Курс")),
                            title=str(item.get("title", "Задача")),
                            due_date=str(item.get("due_date", today.isoformat())),
                            priority=str(item.get("priority", "medium")),  # type: ignore[arg-type]
                        )
                        if r.get("ok"):
                            added_count += 1
                    workspace["state"]["deadlines"] = get_deadline_store()
                    st.session_state.pop("syllabus_candidates", None)
                    msg = f"### Импорт из силлабуса завершён\n\nДобавлено задач в расписание: **{added_count}**."
                    workspace["messages"].append(
                        {
                            "role": "assistant",
                            "response": {"answer": msg, "steps": [], "meta": {"backend": "local"}},
                        }
                    )
                    st.rerun()

    elif chosen == "План на неделю":
        start_val = st.date_input("Дата начала недели", value=today)
        if st.button("Составить учебный план", use_container_width=True):
            prompt_text = f"Составь сбалансированный учебный план на неделю начиная с {start_val.isoformat()}"
            workspace["messages"].append({"role": "user", "content": prompt_text})
            res = workspace["gateway"].query(prompt_text, workspace["state"]).model_dump(mode="json")
            workspace["state"] = res["state"]
            workspace["messages"].append({"role": "assistant", "response": res})
            st.rerun()

    elif chosen == "Проверить репозиторий":
        repo_val = st.text_input(
            "GitHub-репозиторий (owner/repo или URL)",
            value=st.session_state.get("github_repo", "znaukitai/CampusPulseAI_BadPiggies"),
        )
        files_val = st.text_input(
            "Ожидаемые файлы (через запятую, необязательно)",
            value="README.md, requirements.txt",
        )
        if st.button("Выполнить проверку", use_container_width=True):
            clean_repo = repo_val.strip()
            if clean_repo:
                st.session_state.github_repo = clean_repo
                os.environ["GITHUB_REPOSITORY"] = clean_repo
            prompt_text = f"Проверь готовность репозитория {clean_repo}"
            if files_val.strip():
                prompt_text += f" (файлы: {files_val.strip()})"
            workspace["messages"].append({"role": "user", "content": prompt_text})
            res = workspace["gateway"].query(prompt_text, workspace["state"]).model_dump(mode="json")
            workspace["state"] = res["state"]
            workspace["messages"].append({"role": "assistant", "response": res})
            st.rerun()

    elif chosen == "Найти аудиторию":
        place_query = st.text_input(
            "Номер кабинета или название места в AITU",
            placeholder="Например: C1.2.223, коворкинг, библиотека, деканат",
        )
        if st.button("Найти в кампусе", use_container_width=True):
            q_str = place_query.strip() or "коворкинг"
            prompt_text = f"Где находится {q_str} в кампусе AITU?"
            workspace["messages"].append({"role": "user", "content": prompt_text})
            res = workspace["gateway"].query(prompt_text, workspace["state"]).model_dump(mode="json")
            workspace["state"] = res["state"]
            workspace["messages"].append({"role": "assistant", "response": res})
            st.rerun()
