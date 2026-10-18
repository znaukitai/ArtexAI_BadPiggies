"""Streamlit UI components, theme styles, and deadline cards."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import streamlit as st

from frontend.gateway import ZONE


def apply_theme(theme: str = "dark") -> None:
    """Apply clean dark or light theme CSS."""
    is_dark = theme == "dark"

    bg_main = "#0d0f12" if is_dark else "#f8fafc"
    bg_sidebar = "#13161b" if is_dark else "#f1f5f9"
    bg_surface = "#181c23" if is_dark else "#ffffff"
    bg_hover = "#212630" if is_dark else "#e2e8f0"
    border_col = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(15, 23, 42, 0.1)"
    text_primary = "#f1f5f9" if is_dark else "#0f172a"
    text_muted = "#94a3b8" if is_dark else "#64748b"
    accent = "#3b82f6" if is_dark else "#2563eb"
    glow = "radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.10), transparent 60%)" if is_dark else "radial-gradient(circle at 50% 0%, rgba(37, 99, 235, 0.06), transparent 60%)"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {bg_main};
            background-image: {glow};
            color: {text_primary};
        }}
        [data-testid="stHeader"] {{
            background: transparent !important;
        }}
        [data-testid="stSidebar"] {{
            background-color: {bg_sidebar} !important;
            border-right: 1px solid {border_col};
        }}
        [data-testid="stSidebar"] * {{
            color: {text_primary};
        }}
        .block-container {{
            max-width: 880px !important;
            padding-top: 2rem !important;
            padding-bottom: 4rem !important;
        }}
        .stButton > button {{
            background-color: {bg_surface} !important;
            color: {text_primary} !important;
            border: 1px solid {border_col} !important;
            border-radius: 14px !important;
            padding: 0.55rem 0.9rem !important;
            font-size: 0.86rem !important;
            font-weight: 500 !important;
            text-align: left !important;
            transition: background-color 0.15s ease, border-color 0.15s ease;
        }}
        .stButton > button:hover {{
            background-color: {bg_hover} !important;
            border-color: {accent} !important;
        }}
        [data-testid="stChatMessage"] {{
            background-color: {bg_surface};
            border: 1px solid {border_col};
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.75rem;
        }}
        [data-testid="stChatInput"] {{
            border-radius: 20px !important;
        }}
        .hero-box {{
            text-align: center;
            padding: 2.5rem 1rem 1.5rem 1rem;
        }}
        .hero-title {{
            font-size: 2rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 0.4rem;
            color: {text_primary};
        }}
        .hero-sub {{
            font-size: 0.95rem;
            color: {text_muted};
            margin-bottom: 1.5rem;
        }}
        .dl-item {{
            background-color: {bg_surface};
            border: 1px solid {border_col};
            border-radius: 12px;
            padding: 0.65rem 0.8rem;
            margin-bottom: 0.5rem;
        }}
        .dl-course {{
            font-size: 0.72rem;
            color: {accent};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        .dl-title {{
            font-size: 0.85rem;
            font-weight: 500;
            color: {text_primary};
            margin: 0.15rem 0 0.3rem 0;
        }}
        .dl-meta {{
            font-size: 0.75rem;
            color: {text_muted};
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .repo-pill {{
            display: inline-block;
            background-color: {bg_surface};
            border: 1px solid {border_col};
            border-radius: 10px;
            padding: 0.4rem 0.7rem;
            font-size: 0.78rem;
            margin-top: 0.25rem;
            width: 100%;
        }}
        .repo-pill a {{
            color: {accent} !important;
            text-decoration: none;
            font-weight: 500;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_deadlines(state: dict[str, Any]) -> None:
    """Render compact deadline list in the sidebar."""
    deadlines = state.get("deadlines", [])
    if not isinstance(deadlines, list):
        return

    active = [
        d for d in deadlines
        if isinstance(d, dict) and d.get("status") not in {"done", "completed"}
    ]
    if not active:
        st.caption("Активных дедлайнов нет.")
        return

    today = datetime.now(ZONE).date()
    for task in sorted(active, key=lambda d: str(d.get("due_date", "9999"))):
        title = str(task.get("title", "Без названия"))
        course = str(task.get("course", "Курс"))
        due_str = str(task.get("due_date", "—"))
        try:
            delta = (date.fromisoformat(due_str[:10]) - today).days
            if delta < 0:
                badge = "🔴 Просрочено"
            elif delta == 0:
                badge = "🟠 Сегодня"
            elif delta <= 3:
                badge = f"🟡 {delta} дн."
            else:
                badge = f"🔵 {delta} дн."
        except ValueError:
            badge = "⚪ —"

        st.markdown(
            f"""
            <div class="dl-item">
                <div class="dl-course">{course}</div>
                <div class="dl-title">{title}</div>
                <div class="dl-meta">
                    <span>{due_str}</span>
                    <span>{badge}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_response(response: dict[str, Any]) -> None:
    """Render assistant message cleanly without execution trace."""
    st.markdown(response.get("answer", ""))
