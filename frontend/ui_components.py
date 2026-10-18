"""Streamlit UI components, theme styles, and deadline cards."""

from __future__ import annotations

import html
import json
import os
from datetime import date, datetime
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
from frontend.gateway import ZONE
from frontend.icons import get_icon


def inject_theme(mode: str = "dark") -> None:
    """Inject CSS variables and theme rules for dark or light mode."""
    is_dark = mode == "dark"
    scheme = "dark" if is_dark else "light"

    bg = "#0B0F17" if is_dark else "#FAFAFA"
    surface = "#111827" if is_dark else "#FFFFFF"
    surface2 = "#1A2232" if is_dark else "#F4F4F5"
    border = "rgba(255, 255, 255, 0.08)" if is_dark else "#E4E4E7"
    text_col = "#E6EAF2" if is_dark else "#18181B"
    text_muted = "#9AA4B5" if is_dark else "#52525B"
    accent = "#35C3CF" if is_dark else "#0B7C87"
    accent_ring = "rgba(53, 195, 207, 0.28)" if is_dark else "rgba(11, 124, 135, 0.24)"
    live_fg = "#3DD68C" if is_dark else "#15803D"
    live_bg = "rgba(61, 214, 140, 0.12)" if is_dark else "rgba(21, 128, 61, 0.12)"
    demo_fg = "#FDA14A" if is_dark else "#B45309"
    demo_bg = "rgba(253, 161, 74, 0.12)" if is_dark else "rgba(180, 83, 9, 0.12)"
    err_fg = "#F97066" if is_dark else "#C0261B"
    err_bg = "rgba(249, 112, 102, 0.12)" if is_dark else "rgba(192, 38, 27, 0.12)"
    shadow_float = (
        "0 8px 24px rgba(0, 0, 0, 0.35)"
        if is_dark
        else "0 6px 20px rgba(24, 24, 27, 0.08)"
    )

    st.markdown(
        f"""
        <style>
        :root, html, body, .stApp {{
            color-scheme: {scheme};
            --cp-bg: {bg};
            --cp-surface: {surface};
            --cp-surface-2: {surface2};
            --cp-border: {border};
            --cp-text: {text_col};
            --cp-text-muted: {text_muted};
            --cp-accent: {accent};
            --cp-accent-ring: {accent_ring};
            --cp-live-fg: {live_fg};
            --cp-live-bg: {live_bg};
            --cp-demo-fg: {demo_fg};
            --cp-demo-bg: {demo_bg};
            --cp-err-fg: {err_fg};
            --cp-err-bg: {err_bg};
            --cp-shadow: {shadow_float};
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 15px;
            background-color: var(--cp-bg) !important;
            background-image: none !important;
            color: var(--cp-text);
        }}

        /* Single owner of page background — transparent layout containers */
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stHeader"],
        [data-testid="stBottom"],
        [data-testid="stBottom"] > div,
        [data-testid="stBottomBlockContainer"],
        [data-testid="stBottomBlockContainer"] > div {{
            background: transparent !important;
            background-color: transparent !important;
            background-image: none !important;
        }}

        /* Hide Deploy button and developer menu */
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"],
        [data-testid="stToolbar"] {{
            display: none !important;
        }}

        /* Typography across all elements */
        .stApp,
        .stApp p,
        .stApp li,
        .stApp ul,
        .stApp ol,
        .stApp span,
        .stApp label,
        .stApp td,
        .stApp th,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stChatMessageContent"],
        [data-testid="stChatMessageContent"] p,
        [data-testid="stChatMessageContent"] li,
        [data-testid="stExpander"] summary,
        [data-testid="stExpanderDetails"],
        [data-testid="stPopoverBody"],
        [data-testid="stDialog"] {{
            color: var(--cp-text);
            font-size: 15px;
            line-height: 1.55;
        }}

        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
            color: var(--cp-text);
            font-weight: 600;
            letter-spacing: -0.015em;
        }}
        .stApp h1 {{ font-size: 28px; }}
        .stApp h2 {{ font-size: 22px; }}
        .stApp h3 {{ font-size: 20px; }}

        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p,
        .cp-muted {{
            color: var(--cp-text-muted) !important;
            font-size: 13px !important;
        }}

        /* Neutral inline code and code blocks */
        .stApp code {{
            background-color: var(--cp-surface-2);
            color: var(--cp-text);
            border: 1px solid var(--cp-border);
            border-radius: 6px;
            padding: 2px 6px;
            font-size: 13px;
        }}
        .stApp pre, .stApp pre code {{
            background-color: var(--cp-surface-2);
            color: var(--cp-text);
            border-radius: 10px;
        }}

        /* Tables */
        .stApp table {{
            border-collapse: collapse;
            width: 100%;
            background-color: var(--cp-surface);
            border: 1px solid var(--cp-border);
            border-radius: 10px;
            overflow: hidden;
        }}
        .stApp th, .stApp td {{
            border: 1px solid var(--cp-border);
            padding: 8px 12px;
            color: var(--cp-text);
        }}
        .stApp th {{
            background-color: var(--cp-surface-2);
            font-weight: 600;
        }}

        /* Sidebar */
        [data-testid="stSidebar"],
        [data-testid="stSidebarContent"] {{
            background-color: var(--cp-surface) !important;
            border-right: 1px solid var(--cp-border);
            color: var(--cp-text);
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4 {{
            color: var(--cp-text);
        }}

        /* Main column width */
        [data-testid="stMainBlockContainer"] {{
            max-width: 880px;
            padding-top: 24px;
            padding-bottom: 48px;
        }}
        [data-testid="stBottomBlockContainer"] {{
            max-width: 880px;
            padding-top: 8px;
            padding-bottom: 16px;
        }}

        /* Buttons */
        .stButton > button,
        [data-testid="stLinkButton"] > a,
        [data-testid="stPopover"] > div > button {{
            background-color: var(--cp-surface);
            color: var(--cp-text);
            border: 1px solid var(--cp-border);
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 14px;
            font-weight: 500;
            transition: background-color 180ms ease, border-color 180ms ease, transform 180ms ease;
        }}
        .stButton > button:hover,
        [data-testid="stLinkButton"] > a:hover,
        [data-testid="stPopover"] > div > button:hover {{
            background-color: var(--cp-surface-2);
            border-color: var(--cp-accent);
            color: var(--cp-text);
        }}
        .stButton > button:focus-visible,
        [data-testid="stPopover"] > div > button:focus-visible {{
            outline: none;
            border-color: var(--cp-accent);
            box-shadow: 0 0 0 3px var(--cp-accent-ring);
        }}

        /* Inputs, textareas, selects */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stDateInput"] input,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
            background-color: var(--cp-surface-2);
            color: var(--cp-text);
            border: 1px solid var(--cp-border);
            border-radius: 10px;
        }}
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stChatInputTextArea"]::placeholder {{
            color: var(--cp-text-muted);
            opacity: 1;
        }}
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {{
            border-color: var(--cp-accent);
            box-shadow: 0 0 0 3px var(--cp-accent-ring);
            outline: none;
        }}

        /* Expanders, Popovers, Dialogs */
        [data-testid="stExpander"] {{
            background-color: var(--cp-surface);
            border: 1px solid var(--cp-border);
            border-radius: 14px;
            overflow: hidden;
        }}
        [data-testid="stPopoverBody"],
        [data-testid="stDialog"] > div {{
            background-color: var(--cp-surface);
            color: var(--cp-text);
            border: 1px solid var(--cp-border);
            border-radius: 14px;
            box-shadow: var(--cp-shadow);
        }}

        /* Chat messages & neutral avatars */
        [data-testid="stChatMessage"] {{
            background-color: var(--cp-surface);
            border: 1px solid var(--cp-border);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessageAvatarAssistant"],
        [data-testid="stChatMessageAvatarCustom"] {{
            background-color: var(--cp-surface-2) !important;
            color: var(--cp-text) !important;
            border: 1px solid var(--cp-border);
        }}

        /* Floating pill chat input — single border, no inner seams */
        [data-testid="stChatInput"] {{
            background-color: var(--cp-surface);
            border: 1px solid var(--cp-border);
            border-radius: 20px;
            box-shadow: var(--cp-shadow);
            padding: 4px 8px;
            transition: border-color 180ms ease, box-shadow 180ms ease;
        }}
        [data-testid="stChatInput"]:focus-within {{
            border-color: var(--cp-accent);
            box-shadow: 0 0 0 3px var(--cp-accent-ring), var(--cp-shadow);
        }}
        [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] > div > div,
        [data-testid="stChatInputTextArea"],
        [data-testid="stChatInputSubmitButton"] {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: var(--cp-text);
        }}
        [data-testid="stChatInputSubmitButton"]:hover {{
            color: var(--cp-accent);
        }}

        /* Iframe container */
        [data-testid="stIFrame"],
        .stApp iframe {{
            background-color: var(--cp-surface);
            border-radius: 14px;
            border: 1px solid var(--cp-border);
        }}

        /* Hero section */
        .hero-box {{
            text-align: center;
            padding: 36px 16px 24px 16px;
        }}
        .hero-title {{
            font-size: 28px;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
            color: var(--cp-text);
        }}
        .hero-sub {{
            font-size: 15px;
            color: var(--cp-text-muted);
            margin-bottom: 20px;
        }}

        /* Deadline card */
        .dl-item {{
            background-color: var(--cp-surface-2);
            border: 1px solid var(--cp-border);
            border-radius: 14px;
            padding: 12px;
            margin-bottom: 8px;
        }}
        .dl-course {{
            font-size: 12px;
            color: var(--cp-accent);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .dl-title {{
            font-size: 14px;
            font-weight: 500;
            color: var(--cp-text);
            margin: 4px 0 8px 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .dl-meta {{
            font-size: 13px;
            color: var(--cp-text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
        }}

        /* Semantic badges (LIVE / DEMO / Error) */
        .cp-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            line-height: 1.4;
        }}
        .cp-badge-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            display: inline-block;
        }}
        .cp-badge-live {{
            background-color: var(--cp-live-bg);
            color: var(--cp-live-fg);
        }}
        .cp-badge-live .cp-badge-dot {{
            background-color: var(--cp-live-fg);
        }}
        .cp-badge-demo {{
            background-color: var(--cp-demo-bg);
            color: var(--cp-demo-fg);
        }}
        .cp-badge-demo .cp-badge-dot {{
            background-color: var(--cp-demo-fg);
        }}
        .cp-badge-err {{
            background-color: var(--cp-err-bg);
            color: var(--cp-err-fg);
        }}
        .cp-badge-err .cp-badge-dot {{
            background-color: var(--cp-err-fg);
        }}

        /* Agent execution trace */
        .cp-trace-meta {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            margin-bottom: 10px;
            background-color: var(--cp-surface);
            border: 1px solid var(--cp-border);
            border-radius: 10px;
            font-size: 13px;
            color: var(--cp-text-muted);
        }}
        .cp-step-card {{
            background-color: var(--cp-surface);
            border: 1px solid var(--cp-border);
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 8px;
            font-size: 13px;
            color: var(--cp-text);
        }}
        .cp-step-header {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 6px;
        }}
        .cp-step-title {{
            font-weight: 600;
            color: var(--cp-text);
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        .cp-step-tool {{
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 6px;
            background-color: var(--cp-surface-2);
            border: 1px solid var(--cp-border);
            color: var(--cp-accent);
        }}
        .cp-step-body {{
            color: var(--cp-text-muted);
            font-size: 13px;
            line-height: 1.5;
        }}
        .cp-step-details summary {{
            cursor: pointer;
            color: var(--cp-accent);
            font-size: 12px;
            font-weight: 500;
            margin-top: 4px;
            user-select: none;
        }}
        .cp-step-details pre {{
            margin-top: 6px;
            padding: 8px 10px;
            border-radius: 8px;
            background-color: var(--cp-surface-2);
            border: 1px solid var(--cp-border);
            color: var(--cp-text);
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}

        .repo-pill {{
            display: flex;
            align-items: center;
            gap: 8px;
            background-color: var(--cp-surface-2);
            border: 1px solid var(--cp-border);
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 13px;
            margin-top: 4px;
            width: 100%;
            color: var(--cp-text);
        }}
        .repo-pill a {{
            color: var(--cp-accent) !important;
            text-decoration: none;
            font-weight: 500;
            word-break: break-all;
        }}

        /* Circular + action button (NEW-01) */
        .st-key-plus_action_btn button,
        .st-key-empty_plus_btn button {{
            width: 38px !important;
            height: 38px !important;
            min-width: 38px !important;
            min-height: 38px !important;
            border-radius: 50% !important;
            padding: 0 !important;
            background-color: var(--cp-accent) !important;
            color: #0B0F17 !important;
            border: none !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: var(--cp-shadow) !important;
        }}
        .st-key-plus_action_btn button *,
        .st-key-empty_plus_btn button * {{
            color: #0B0F17 !important;
            fill: #0B0F17 !important;
        }}
        .st-key-plus_action_btn button:hover,
        .st-key-empty_plus_btn button:hover {{
            opacity: 0.92 !important;
            transform: scale(1.03);
        }}

        .cp-today-line {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: var(--cp-text-muted);
            padding: 4px 0 8px 0;
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                transition: none !important;
                animation: none !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_theme(theme: str = "dark") -> None:
    """Backward-compatible alias for inject_theme."""
    inject_theme(theme)


def format_badge_html(source: str | None) -> str:
    """Render semantic LIVE, DEMO, or ERROR badge HTML."""
    src = (source or "").strip().lower()
    if src == "live":
        return '<span class="cp-badge cp-badge-live"><span class="cp-badge-dot"></span>LIVE</span>'
    if src in {"error", "err", "cloud-error"}:
        return '<span class="cp-badge cp-badge-err"><span class="cp-badge-dot"></span>ERROR</span>'
    return '<span class="cp-badge cp-badge-demo"><span class="cp-badge-dot"></span>DEMO</span>'


_GROUP_LABELS_RU = [
    ("overdue", "Просрочено"),
    ("today", "Сегодня"),
    ("this_week", "На этой неделе"),
    ("later", "Позже"),
]


def _render_single_deadline_card(
    task: dict[str, Any],
    today: date,
    state: dict[str, Any],
) -> None:
    """Render one deadline card and its quick action buttons."""
    from mcp_servers.academic_schedule import set_deadline_store

    task_id = str(task.get("id", ""))
    raw_title = str(task.get("title", "Без названия"))
    raw_course = str(task.get("course", "Курс"))
    title = html.escape(raw_title)
    course = html.escape(raw_course)
    raw_due = str(task.get("due_date", "—"))
    due_str = html.escape(format_date_ru(raw_due))
    prio_ru = html.escape(format_priority_ru(str(task.get("priority", "medium"))))

    try:
        delta, urg_code = calculate_urgency(raw_due, today)
        urg_ru = format_urgency_ru(urg_code)
        days_ru = format_days_left_ru(delta)
        urg_icon = (
            get_icon("alert_triangle")
            if urg_code in {"overdue", "urgent"}
            else get_icon("clock")
        )
        badge_text = html.escape(f"{urg_ru} · {days_ru}")
        badge = f'<span style="display:inline-flex;align-items:center;gap:4px;">{urg_icon}<span>{badge_text}</span></span>'
    except ValueError:
        badge = "—"

    source_badge = (
        format_badge_html("demo")
        if str(task.get("source", "demo")).lower() == "demo"
        else ""
    )
    cal_icon = get_icon("calendar")

    st.markdown(
        f"""
        <div class="dl-item">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
                <div class="dl-course">{course}</div>
                {source_badge}
            </div>
            <div class="dl-title">{title}</div>
            <div class="dl-meta">
                <span style="display:inline-flex;align-items:center;gap:4px;">{cal_icon}<span>{due_str} · {prio_ru}</span></span>
                {badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        c_done, c_ask, c_del = st.columns([1, 1, 1])
        with c_done:
            if st.button(
                "",
                icon=":material/check:",
                key=f"done_{task_id}",
                help="Выполнено",
                use_container_width=True,
            ):
                updated, _ = complete_deadline(state.get("deadlines", []), task_id)
                state["deadlines"] = updated
                set_deadline_store(updated)
                st.rerun()
        with c_ask:
            if st.button(
                "",
                icon=":material/chat:",
                key=f"ask_{task_id}",
                help="Спросить агента",
                use_container_width=True,
            ):
                st.session_state["chat_input_box"] = (
                    f"С чего начать по задаче «{raw_title}» ({raw_course})?"
                )
                st.rerun()
        with c_del:
            if st.button(
                "",
                icon=":material/delete:",
                key=f"del_{task_id}",
                help="Удалить",
                use_container_width=True,
            ):
                st.session_state[confirm_key] = True
                st.rerun()


def render_deadlines(
    state: dict[str, Any],
    workspace: dict[str, Any] | None = None,
) -> None:
    """Render smart grouped deadline panel in the sidebar (NEW-02)."""
    deadlines = state.get("deadlines", [])
    if not isinstance(deadlines, list):
        return

    today = datetime.now(ZONE).date()
    groups = group_deadlines_by_horizon(deadlines, today)
    total_active = sum(len(items) for items in groups.values())

    if total_active == 0:
        st.markdown(
            '<div style="text-align:center;padding:14px 8px;color:var(--cp-text-muted);font-size:13px;">Дедлайнов пока нет</div>',
            unsafe_allow_html=True,
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
                    _render_single_deadline_card(task, today, state)
        else:
            st.markdown(
                f'<div style="font-size:12px;font-weight:600;color:var(--cp-text-muted);text-transform:uppercase;letter-spacing:0.04em;margin:10px 0 6px 0;">{html.escape(header_label)}</div>',
                unsafe_allow_html=True,
            )
            for task in items:
                _render_single_deadline_card(task, today, state)



_STEP_TYPE_LABELS = {
    "thought": "Размышление",
    "tool_call": "Вызов инструмента",
    "tool_result": "Результат инструмента",
    "final": "Формирование ответа",
    "error": "Ошибка",
}


def render_response(response: dict[str, Any]) -> None:
    """Render assistant message and collapsible execution trace with LIVE/DEMO badges."""
    st.markdown(response.get("answer", ""))

    steps = response.get("steps") or []
    meta = response.get("meta") or {}
    if not isinstance(steps, list) or not steps:
        return

    backend = str(meta.get("backend", "local-orchestrator"))
    model_name = html.escape(str(meta.get("model", "mcp-orchestrator")))
    total_ms = int(meta.get("total_ms", 0) or 0)
    tool_calls_count = int(meta.get("tool_calls", 0) or 0)

    has_error = backend in {"error", "cloud-error"} or any(
        isinstance(s, dict) and s.get("type") == "error" for s in steps
    )
    if has_error:
        overall_badge = format_badge_html("error")
    elif backend in {"local", "cloud"}:
        overall_badge = format_badge_html("live")
    else:
        overall_badge = format_badge_html("demo")

    with st.expander("Как агент пришёл к ответу", expanded=False):
        st.markdown(
            f"""
            <div class="cp-trace-meta">
                {overall_badge}
                <span>Модель: <strong>{model_name}</strong></span>
                <span>Вызовов MCP: <strong>{tool_calls_count}</strong></span>
                <span>Время: <strong>{total_ms} мс</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            stype = str(step.get("type", "thought"))
            type_label = html.escape(_STEP_TYPE_LABELS.get(stype, stype))
            tool_name = step.get("name")
            tool_html = (
                f'<span class="cp-step-tool">{html.escape(str(tool_name))}</span>'
                if tool_name
                else ""
            )
            dur = step.get("duration_ms")
            dur_html = f"<span>{int(dur)} мс</span>" if dur is not None else ""

            if stype == "error":
                badge_html = format_badge_html("error")
            elif step.get("source"):
                badge_html = format_badge_html(str(step.get("source")))
            else:
                badge_html = ""

            body_parts: list[str] = []
            if step.get("thought"):
                body_parts.append(
                    f'<div class="cp-step-body">{html.escape(str(step["thought"]))}</div>'
                )
            if step.get("args") is not None:
                args_json = html.escape(
                    json.dumps(step["args"], ensure_ascii=False, indent=2)
                )
                body_parts.append(
                    f'<details class="cp-step-details"><summary>Аргументы вызова</summary><pre>{args_json}</pre></details>'
                )
            if step.get("result") is not None:
                res_json = html.escape(
                    json.dumps(step["result"], ensure_ascii=False, indent=2)
                )
                body_parts.append(
                    f'<details class="cp-step-details"><summary>Результат JSON</summary><pre>{res_json}</pre></details>'
                )

            body_html = "".join(body_parts)
            st.markdown(
                f"""
                <div class="cp-step-card">
                    <div class="cp-step-header">
                        <span class="cp-step-title">#{idx} {type_label} {tool_html}</span>
                        <span style="display:inline-flex;align-items:center;gap:8px;color:var(--cp-text-muted);font-size:12px;">
                            {dur_html}
                            {badge_html}
                        </span>
                    </div>
                    {body_html}
                </div>
                """,
                unsafe_allow_html=True,
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
    from datetime import timedelta
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
            course = st.text_input("Курс", value="AI & LLM Engineering", placeholder="Например: CS301 Distributed Systems")
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
                    workspace["messages"].append({"role": "assistant", "response": {"answer": msg, "steps": [], "meta": {"backend": "local"}}})
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
            value=default_syllabus or "CS301 - Lab 5 Raft Replication due 2026-10-24 [high]\nAI & LLM - Final Project Demo due 2026-10-29 [critical]",
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
                    workspace["messages"].append({"role": "assistant", "response": {"answer": msg, "steps": [], "meta": {"backend": "local"}}})
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


