"""Run from project root: python -m streamlit run frontend/app.py."""

import html
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

from frontend.gateway import DEFAULT_REPO, Gateway, GatewayError
from frontend.icons import get_avatar_uri, get_icon
from frontend.ui_components import apply_theme, inject_theme, render_deadlines, render_response
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

with st.sidebar:
    col_brand, col_theme = st.columns([4, 1])
    with col_brand:
        brand_svg = get_icon("brand_pulse")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;font-size:20px;font-weight:600;color:var(--cp-text);padding:4px 0;"><span style="color:var(--cp-accent);display:inline-flex;">{brand_svg}</span><span>CampusPulse</span></div>',
            unsafe_allow_html=True,
        )
    with col_theme:
        theme_icon = ":material/light_mode:" if st.session_state.theme == "dark" else ":material/dark_mode:"
        if st.button("", icon=theme_icon, key="theme_btn", help="Переключить тему"):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()

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
    st.caption(workspace["status"])

    active_repo = st.session_state.github_repo or DEFAULT_REPO
    repo_url = active_repo if active_repo.startswith("https://github.com/") else f"https://github.com/{active_repo}"
    safe_repo_url = html.escape(repo_url, quote=True)
    safe_active_repo = html.escape(active_repo)
    gh_svg = get_icon("github")
    st.markdown(
        f'<div class="repo-pill"><span style="color:var(--cp-accent);display:inline-flex;">{gh_svg}</span><a href="{safe_repo_url}" target="_blank" rel="noopener noreferrer">{safe_active_repo}</a></div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Дедлайны")
    render_deadlines(workspace["state"])

selected_prompt = None

if not workspace["messages"]:
    st.markdown(
        """
        <div class="hero-box">
            <div class="hero-title">Чем помочь по учёбе сегодня?</div>
            <div class="hero-sub">Дедлайны AITU, проверка GitHub, расписание на неделю и карта корпусов C1</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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

for message in workspace["messages"]:
    role = message["role"]
    avatar_uri = user_avatar if role == "user" else assistant_avatar
    with st.chat_message(role, avatar=avatar_uri):
        if role == "user":
            st.markdown(message["content"])
        elif "response" in message:
            render_response(message["response"])
        else:
            st.error(message["content"])

typed_prompt = st.chat_input("Спросите о дедлайнах, GitHub или аудитории в кампусе...", max_chars=10000)

if prompt := selected_prompt or typed_prompt:
    workspace["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar=assistant_avatar):
        try:
            with st.spinner("Думаю..."):
                response = workspace["gateway"].query(prompt, workspace["state"]).model_dump(mode="json")
            workspace["state"] = response["state"]
            workspace["messages"].append({"role": "assistant", "response": response})
            st.rerun()
        except GatewayError as exc:
            workspace["messages"].append({"role": "assistant", "content": str(exc)})
            st.rerun()
