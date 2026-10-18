# Run from project root: python -m streamlit run frontend/app.py

import html
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

from core.deadline_logic import format_date_ru
from frontend.components import (
    open_action_dialog,
    render_deadlines,
    render_empty_state,
    render_error_card,
    render_loading_state,
    render_mode_badge,
    render_response,
)
from frontend.gateway import DEFAULT_REPO, ZONE, Gateway, GatewayError
from frontend.icons import get_avatar_uri, icon
from frontend.theme import inject_theme
from mcp_servers.academic_schedule import get_default_deadlines, reset_deadline_store

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="CampusPulse", layout="wide")

PROMPTS = [
    ("Что горит на этой неделе?", "Что горит на этой неделе и с чего начать?"),
    ("Проверить GitHub-репозиторий", "Проверь готовность репозитория лабы по алгоритмам"),
    ("План учёбы на неделю", "Составь сбалансированный учебный план на неделю"),
    ("Найти коворкинг в C1", "Где находится коворкинг в корпусе C1?"),
]

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
if "github_repo" not in st.session_state:
    st.session_state.github_repo = os.getenv("GITHUB_REPOSITORY", DEFAULT_REPO) or DEFAULT_REPO
if "gcp_project" not in st.session_state:
    st.session_state.gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
if "vertex_resource" not in st.session_state:
    st.session_state.vertex_resource = os.getenv("VERTEX_AGENT_RESOURCE", "")

inject_theme(st.session_state.theme)


def _render_sidebar_html(markup: str) -> None:
    clean = " ".join(line.strip() for line in markup.splitlines() if line.strip())
    if hasattr(st, "html"):
        st.html(clean)
    else:
        st.markdown(clean, unsafe_allow_html=True)


with st.sidebar:
    brand_svg = icon("logo", size=20)
    _render_sidebar_html(
        f'<div class="cp-brand-row">'
        f'<span class="cp-brand-icon">{brand_svg}</span>'
        f"<span>CampusPulse</span>"
        f"</div>"
    )

    if st.button("Новый чат", icon=":material/add:", use_container_width=True):
        reset_deadline_store()
        st.session_state.pop("workspace", None)
        st.rerun()

    with st.expander("Подключение и GitHub", icon=":material/settings:", expanded=False):
        mode_label = st.radio(
            "Режим",
            ["Local", "Cloud (Vertex AI)"],
            horizontal=True,
        )
        mode = "local" if mode_label == "Local" else "cloud"

        if mode == "local":
            api_key_input = st.text_input(
                "Gemini API Key",
                value=st.session_state.gemini_api_key,
                type="password",
                placeholder="AIza...",
                help="Необязательно. Ключ хранится только в памяти текущей сессии.",
            )
            if api_key_input.strip() != st.session_state.gemini_api_key:
                st.session_state.gemini_api_key = api_key_input.strip()
                st.session_state.pop("workspace", None)
        else:
            gcp_proj_input = st.text_input(
                "Google Cloud Project ID",
                value=st.session_state.gcp_project,
                placeholder="my-gcp-project-id",
                help="ID проекта Google Cloud для Vertex AI (требуется ADC: gcloud auth application-default login).",
            )
            vertex_res_input = st.text_input(
                "Vertex Agent Resource (опционально)",
                value=st.session_state.vertex_resource,
                placeholder="projects/.../locations/.../reasoningEngines/...",
                help="Оставьте пустым для прямого вызова Gemini через Vertex AI ADC.",
            )
            if gcp_proj_input.strip() != st.session_state.gcp_project:
                st.session_state.gcp_project = gcp_proj_input.strip()
                st.session_state.pop("workspace", None)
            if vertex_res_input.strip() != st.session_state.vertex_resource:
                st.session_state.vertex_resource = vertex_res_input.strip()
                st.session_state.pop("workspace", None)

        repo_input = st.text_input(
            "GitHub репозиторий",
            value=st.session_state.github_repo,
            placeholder="owner/repo",
        )
        if repo_input.strip() and repo_input.strip() != st.session_state.github_repo:
            st.session_state.github_repo = repo_input.strip()
            os.environ["GITHUB_REPOSITORY"] = st.session_state.github_repo

    if st.session_state.get("mode") != mode:
        st.session_state.pop("workspace", None)
        st.session_state.mode = mode

    if "workspace" not in st.session_state:
        try:
            gateway = Gateway(
                mode,
                api_key=st.session_state.gemini_api_key,
                project=st.session_state.gcp_project,
                resource=st.session_state.vertex_resource,
            )
            st.session_state.workspace = {
                "gateway": gateway,
                "state": {"deadlines": get_default_deadlines()},
                "messages": [],
                "status": gateway.backend.status,
            }
        except GatewayError as exc:
            st.warning(str(exc))
            fallback_gw = Gateway("local", api_key=st.session_state.gemini_api_key)
            st.session_state.workspace = {
                "gateway": fallback_gw,
                "state": {"deadlines": get_default_deadlines()},
                "messages": [],
                "status": str(exc),
            }

    workspace = st.session_state.workspace
    status_str = str(workspace["status"])
    is_live_conn = "LIVE" in status_str.upper()
    mode_badge = render_mode_badge(is_live_conn)
    safe_status = html.escape(status_str)
    _render_sidebar_html(
        f'<div class="cp-status-row">'
        f"{mode_badge}"
        f'<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{safe_status}">{safe_status}</span>'
        f"</div>"
    )

    today_ru = format_date_ru(datetime.now(ZONE).date().isoformat(), with_year=True)
    cal_svg = icon("calendar_clock", size=16)
    _render_sidebar_html(
        f'<div class="cp-today-line">'
        f'<span style="color:var(--cp-accent);display:inline-flex;">{cal_svg}</span>'
        f"<span>Сегодня: <strong>{html.escape(today_ru)}</strong></span>"
        f"</div>"
    )

    active_repo = st.session_state.github_repo or DEFAULT_REPO
    repo_url = active_repo if active_repo.startswith("https://github.com/") else f"https://github.com/{active_repo}"
    safe_repo_url = html.escape(repo_url, quote=True)
    safe_active_repo = html.escape(active_repo)
    branch_svg = icon("branch", size=15)
    _render_sidebar_html(
        f'<div class="repo-pill" title="{safe_active_repo}">'
        f'<span style="color:var(--cp-accent);display:inline-flex;">{branch_svg}</span>'
        f'<a href="{safe_repo_url}" target="_blank" rel="noopener noreferrer">{safe_active_repo}</a>'
        f"</div>"
    )

    col_dl_hdr, col_dl_plus = st.columns([4, 1], vertical_alignment="center")
    with col_dl_hdr:
        _render_sidebar_html(
            '<div style="font-size:16px;font-weight:600;color:var(--cp-text);letter-spacing:-0.01em;margin:4px 0;">Дедлайны</div>'
        )
    with col_dl_plus:
        if st.button("", icon=":material/add:", key="plus_action_btn", help="Добавить дедлайн или действие"):
            open_action_dialog(workspace)

    render_deadlines(workspace["state"], workspace=workspace)

    _render_sidebar_html('<div style="height:12px;border-top:1px solid var(--cp-border);margin-top:12px;"></div>')
    col_theme_btn, col_theme_lbl = st.columns([1, 4], vertical_alignment="center")
    with col_theme_btn:
        theme_icon = ":material/light_mode:" if st.session_state.theme == "dark" else ":material/dark_mode:"
        if st.button("", icon=theme_icon, key="theme_btn", help="Переключить тему (Тёмная / Светлая)"):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()
    with col_theme_lbl:
        theme_name = "Тёмная тема" if st.session_state.theme == "dark" else "Светлая тема"
        st.caption(theme_name)

selected_prompt = None

if not workspace["messages"]:
    render_empty_state()
    cols = st.columns(2)
    for idx, (short_label, full_prompt) in enumerate(PROMPTS):
        with cols[idx % 2]:
            if st.button(short_label, key=f"chip_{idx}", use_container_width=True):
                selected_prompt = full_prompt

with st.expander("Интерактивная карта кампуса AITU", icon=":material/map:"):
    st.caption("Корпуса C1.1–C1.3, этажи 1–3. Спросите номер кабинета в чате или откройте схему.")
    st.link_button("Открыть карту в новой вкладке", "https://yuujiso.github.io/aitumap/")
    if hasattr(st, "iframe"):
        st.iframe("https://yuujiso.github.io/aitumap/", height=560)
    else:
        import streamlit.components.v1 as components

        components.iframe("https://yuujiso.github.io/aitumap/", height=560, scrolling=False)

user_avatar = get_avatar_uri("user", st.session_state.theme)
assistant_avatar = get_avatar_uri("assistant", st.session_state.theme)

for idx, message in enumerate(workspace["messages"]):
    role = message["role"]
    avatar_uri = user_avatar if role == "user" else assistant_avatar
    with st.chat_message(role, avatar=avatar_uri):
        if role == "user":
            st.markdown(message["content"])
        elif "response" in message:
            render_response(message["response"])
        else:
            retry_prompt = message.get("failed_prompt")
            if render_error_card(message["content"], retry_key=f"retry_msg_{idx}", on_retry_prompt=retry_prompt):
                selected_prompt = retry_prompt

typed_prompt = st.chat_input(
    "Спросите о дедлайнах, GitHub или аудитории в кампусе...",
    max_chars=10000,
    key="chat_input_box",
)

if prompt := selected_prompt or typed_prompt:
    workspace["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar=assistant_avatar):
        loading_slot = st.empty()
        with loading_slot.container():
            render_loading_state()
        try:
            response = workspace["gateway"].query(prompt, workspace["state"]).model_dump(mode="json")
            loading_slot.empty()
            workspace["state"] = response["state"]
            workspace["messages"].append({"role": "assistant", "response": response})
            st.rerun()
        except GatewayError as exc:
            loading_slot.empty()
            workspace["messages"].append(
                {"role": "assistant", "content": str(exc), "failed_prompt": prompt}
            )
            st.rerun()
