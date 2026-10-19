"""Theme tokens, WCAG-checked Dark/Light palettes, and seamless CSS injection for Artex AI."""

from __future__ import annotations

import streamlit as st

PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "color_scheme": "dark",
        "brand": "#3B82F6", "button": "#2563EB", "white": "#FFFFFF", "hover": "#60A5FA",
        "warn_fg": "#F59E0B", "warn_bg": "#312B23", "warn": "#F59E0B",
        "danger": "#EF4444", "success": "#10B981",
        "bg": "#0B0F19",
        "surface": "#111827",
        "surface2": "#1A2233",
        "border": "rgba(226,232,240,.10)",
        "border_strong": "rgba(226,232,240,.18)",
        "text": "#E2E8F0",
        "muted": "#94A3B8",
        "accent": "#3B82F6",
        "accent_soft": "rgba(59,130,246,.12)",
        "accent_ring": "rgba(59,130,246,.28)",
        "live_fg": "#10B981",
        "live_bg": "#112F34",
        "demo_fg": "#94A3B8",
        "demo_bg": "transparent",
        "err_fg": "#FCA5A5",
        "err_bg": "#301E2B",
        "float_shadow": "0 8px 28px rgba(0, 0, 0, 0.36)",
    },
    "light": {
        "color_scheme": "light",
        "brand": "#3B82F6", "button": "#2563EB", "white": "#FFFFFF", "hover": "#2563EB",
        "warn_fg": "#92400E", "warn_bg": "#FEF3C7", "warn": "#F59E0B",
        "danger": "#EF4444", "success": "#10B981",
        "bg": "#F8FAFC",
        "surface": "#FFFFFF",
        "surface2": "#F1F5F9",
        "border": "#E2E8F0",
        "border_strong": "#CBD5E1",
        "text": "#0B0F19",
        "muted": "#475569",
        "accent": "#2563EB",
        "accent_soft": "rgba(37,99,235,.10)",
        "accent_ring": "rgba(59,130,246,.28)",
        "live_fg": "#047857",
        "live_bg": "#D1FAE5",
        "demo_fg": "#475569",
        "demo_bg": "transparent",
        "err_fg": "#B91C1C",
        "err_bg": "#FEE2E2",
        "float_shadow": "0 6px 24px rgba(24, 24, 27, 0.07)",
    },
}


def inject_theme(mode: str = "dark") -> None:
    """Inject CSS variables and seamless layout styles for Dark or Light mode."""
    p = PALETTES["dark" if mode == "dark" else "light"]
    css = f"""<style>
:root, html, body, .stApp {{
    color-scheme: {p["color_scheme"]};
    --cp-brand: {p["brand"]}; --cp-button: {p["button"]}; --cp-white: {p["white"]}; --cp-hover: {p["hover"]};
    --cp-warn-fg: {p["warn_fg"]}; --cp-warn-bg: {p["warn_bg"]}; --cp-warn: {p["warn"]};
    --cp-danger: {p["danger"]}; --cp-success: {p["success"]};
    --cp-bg: {p["bg"]};
    --cp-surface: {p["surface"]};
    --cp-surface-2: {p["surface2"]};
    --cp-border: {p["border"]};
    --cp-border-strong: {p["border_strong"]};
    --cp-text: {p["text"]};
    --cp-muted: {p["muted"]};
    --cp-accent: {p["accent"]};
    --cp-accent-soft: {p["accent_soft"]};
    --cp-accent-ring: {p["accent_ring"]};
    --cp-live-fg: {p["live_fg"]};
    --cp-live-bg: {p["live_bg"]};
    --cp-demo-fg: {p["demo_fg"]};
    --cp-demo-bg: {p["demo_bg"]};
    --cp-err-fg: {p["err_fg"]};
    --cp-err-bg: {p["err_bg"]};
    --cp-float-shadow: {p["float_shadow"]};
    --cp-font-sans: 'Inter', 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --cp-font-mono: 'JetBrains Mono', 'Geist Mono', ui-monospace, SFMono-Regular, Consolas, monospace;
}}

/* Preserve Material Symbols ligature font so Streamlit icons never break */
[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Rounded" !important;
    font-weight: normal !important;
    font-style: normal !important;
    line-height: 1 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-smoothing: antialiased !important;
}}

/* Single flat background owner — zero seams */
html, body, .stApp, [data-testid="stAppViewContainer"] {{
    background: var(--cp-bg) !important;
    background-color: var(--cp-bg) !important;
    background-image: none !important;
    color: var(--cp-text) !important;
    font-family: var(--cp-font-sans);
    font-size: 15px;
    line-height: 1.6;
}}

/* Transparent structural containers */
[data-testid="stHeader"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] > div {{
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    border: none !important;
    box-shadow: none !important;
}}

/* Soft fade above the floating input pill ending strictly at var(--cp-bg) */
[data-testid="stBottom"] {{
    position: relative;
}}
[data-testid="stBottom"]::before {{
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: -28px;
    height: 28px;
    background: linear-gradient(180deg, transparent 0%, var(--cp-bg) 100%);
    pointer-events: none;
    z-index: 0;
}}

/* Hide Deploy button, developer menu, and status widget */
[data-testid="stAppDeployButton"],
[data-testid="stDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
.stDeployButton,
footer {{
    display: none !important;
}}

/* Keep header compact and unobtrusive while preserving sidebar expand button */
[data-testid="stHeader"] {{
    height: 3.25rem !important;
    pointer-events: none;
}}
[data-testid="stHeader"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] {{
    pointer-events: auto !important;
}}

/* Sleek floating sidebar reopen button when collapsed */
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] button {{
    background: var(--cp-surface) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
    box-shadow: var(--cp-float-shadow) !important;
    width: 36px !important;
    height: 36px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: opacity 180ms ease, transform 180ms ease, border-color 180ms ease !important;
}}
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="collapsedControl"] button:hover {{
    border-color: var(--cp-accent) !important;
    color: var(--cp-accent) !important;
    transform: translateX(2px);
}}

/* Center main chat column at max 760px */
[data-testid="stMainBlockContainer"] {{
    max-width: 760px !important;
    margin: 0 auto !important;
    padding-top: 1.5rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
}}
[data-testid="stBottomBlockContainer"] {{
    max-width: 760px !important;
    margin: 0 auto !important;
    padding-top: 0.25rem !important;
    padding-bottom: 1.25rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
    position: relative;
    z-index: 1;
}}

/* Sidebar — separated only by 1px line, smooth collapsible transition */
[data-testid="stSidebar"] {{
    background: var(--cp-surface) !important;
    background-color: var(--cp-surface) !important;
    border-right: 1px solid var(--cp-border) !important;
    box-shadow: none !important;
    transition: transform 220ms cubic-bezier(.4,0,.2,1), width 220ms cubic-bezier(.4,0,.2,1) !important;
}}
[data-testid="stSidebar"] > div:first-child {{
    background: var(--cp-surface) !important;
    padding-top: 1rem !important;
}}
[data-testid="stSidebarCollapseButton"] button {{
    border-radius: 10px !important;
    color: var(--cp-muted) !important;
    background: transparent !important;
    border: none !important;
    transition: color 160ms ease, background-color 160ms ease !important;
}}
[data-testid="stSidebarCollapseButton"] button:hover {{
    color: var(--cp-text) !important;
    background: var(--cp-surface-2) !important;
}}

/* Typography & Inline Code / Pre blocks (both Dark and Light themes) */
.stApp p, .stApp li, .stApp label, .stApp span:not([data-testid="stIconMaterial"]) {{
    color: inherit;
}}
.stApp p, .stApp li {{
    color: var(--cp-text) !important;
    font-size: 15px;
    line-height: 1.6;
}}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
    color: var(--cp-text) !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em;
}}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {{
    color: var(--cp-muted) !important;
    font-size: 13px !important;
    line-height: 1.45 !important;
}}
.stApp code,
[data-testid="stMarkdownContainer"] code {{
    font-family: var(--cp-font-mono) !important;
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 6px !important;
    padding: 2px 6px !important;
    font-size: 12.5px !important;
}}
.stApp pre,
[data-testid="stMarkdownContainer"] pre,
[data-testid="stCode"] pre {{
    font-family: var(--cp-font-mono) !important;
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
}}
.stApp pre code,
[data-testid="stMarkdownContainer"] pre code,
[data-testid="stCode"] pre code {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: var(--cp-text) !important;
}}

/* Tables in markdown */
.stApp table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    font-variant-numeric: tabular-nums;
}}
.stApp th, .stApp td {{
    border: 1px solid var(--cp-border) !important;
    padding: 8px 12px !important;
    text-align: left;
    color: var(--cp-text) !important;
}}
.stApp th {{
    background: var(--cp-surface-2) !important;
    color: var(--cp-text) !important;
    font-weight: 600;
}}

/* Floating Pill Chat Input — single 1px border, radius 20px, accent focus ring */
[data-testid="stChatInput"] {{
    max-width: 760px !important;
    margin: 0 auto !important;
    background: var(--cp-surface) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 20px !important;
    padding: 4px 10px !important;
    box-shadow: var(--cp-float-shadow) !important;
    transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease !important;
}}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}
[data-testid="stChatInput"]:focus-within {{
    border-color: var(--cp-accent) !important;
    box-shadow: 0 0 0 3px var(--cp-accent-ring), var(--cp-float-shadow) !important;
    outline: none !important;
}}
[data-testid="stChatInput"] textarea {{
    color: var(--cp-text) !important;
    background: transparent !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
    caret-color: var(--cp-accent) !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{
    color: var(--cp-muted) !important;
    opacity: 0.85 !important;
}}
[data-testid="stChatInputSubmitButton"] {{
    background: var(--cp-button) !important;
    color: var(--cp-white) !important;
    border: none !important;
    border-radius: 12px !important;
    width: 36px !important;
    height: 36px !important;
    transition: opacity 160ms ease, transform 160ms ease !important;
}}
[data-testid="stChatInputSubmitButton"]:hover:not(:disabled) {{
    opacity: 0.92 !important;
    transform: scale(1.03);
}}
[data-testid="stChatInputSubmitButton"]:disabled {{
    background: var(--cp-surface-2) !important;
    color: var(--cp-muted) !important;
    opacity: 0.55 !important;
}}
[data-testid="stChatInputSubmitButton"] svg {{
    fill: currentColor !important;
}}

/* Chat messages — clean, no heavy border on assistant response */
[data-testid="stChatMessage"] {{
    background: transparent !important;
    border: none !important;
    padding: 12px 4px !important;
    gap: 12px !important;
}}
[data-testid="stChatMessage"] img {{
    width: 30px !important;
    height: 30px !important;
    border-radius: 999px !important;
    flex-shrink: 0;
}}

/* Buttons (Main, Sidebar, and Dialogs) — use descendant 'button' so stTooltipHoverTarget never breaks styling */
.stButton button,
[data-testid="stSidebar"] .stButton button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
[data-testid="stFormSubmitButton"] button,
[data-testid="stLinkButton"] a {{
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    padding: 5px 10px !important;
    min-height: 36px !important;
    box-shadow: none !important;
    transition: background-color 180ms ease, border-color 180ms ease, color 180ms ease, transform 150ms ease !important;
}}
.stButton button p,
[data-testid="stSidebar"] .stButton button p,
[data-testid="stFormSubmitButton"] button p,
[data-testid="stLinkButton"] a p {{
    color: var(--cp-text) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    margin: 0 !important;
    white-space: nowrap !important;
}}
.stButton button:hover,
[data-testid="stSidebar"] .stButton button:hover,
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-secondaryFormSubmit"]:hover,
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stLinkButton"] a:hover {{
    border-color: var(--cp-accent) !important;
    background: var(--cp-surface) !important;
    background-color: var(--cp-surface) !important;
    color: var(--cp-text) !important;
    transform: translateY(-1px);
}}
.stButton button:active,
[data-testid="stSidebar"] .stButton button:active {{
    transform: scale(0.98);
}}
.stButton button:focus-visible,
[data-testid="stLinkButton"] a:focus-visible {{
    outline: none !important;
    border-color: var(--cp-accent) !important;
    box-shadow: 0 0 0 3px var(--cp-accent-ring) !important;
}}

/* Compact 3-column deadline action buttons so 'Удалить' never truncates */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
    gap: 6px !important;
}}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton button {{
    padding: 3px 4px !important;
    min-height: 30px !important;
    font-size: 12px !important;
}}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton button p {{
    font-size: 12px !important;
    letter-spacing: -0.01em !important;
}}

/* Circular '+' button in Deadlines header */
.st-key-plus_action_btn {{
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
}}
.st-key-plus_action_btn button,
[data-testid="stSidebar"] .st-key-plus_action_btn button {{
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    padding: 0 !important;
    border-radius: 999px !important;
    background: var(--cp-button) !important;
    background-color: var(--cp-button) !important;
    color: var(--cp-white) !important;
    border: none !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 8px var(--cp-accent-soft) !important;
    transition: transform 180ms ease, opacity 180ms ease, box-shadow 180ms ease !important;
}}
.st-key-plus_action_btn button [data-testid="stIconMaterial"],
.st-key-plus_action_btn button span {{
    color: var(--cp-white) !important;
    font-size: 18px !important;
}}
.st-key-plus_action_btn button:hover,
[data-testid="stSidebar"] .st-key-plus_action_btn button:hover {{
    background: var(--cp-button) !important;
    background-color: var(--cp-button) !important;
    opacity: 0.92 !important;
    transform: scale(1.05);
    box-shadow: 0 0 0 3px var(--cp-accent-ring) !important;
}}
.st-key-plus_action_btn button:active {{
    transform: scale(0.96);
}}

/* 40x40px Theme toggle button at bottom of sidebar */
.st-key-theme_btn button,
[data-testid="stSidebar"] .st-key-theme_btn button {{
    width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
    border-radius: 10px !important;
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}}
.st-key-theme_btn button:hover,
[data-testid="stSidebar"] .st-key-theme_btn button:hover {{
    border-color: var(--cp-accent) !important;
    color: var(--cp-accent) !important;
}}

/* Modal Dialogs (st.dialog), Popovers, Tooltips, Select Dropdowns, and Calendar Datepicker in Portal */
[role="dialog"],
[role="dialog"] > div,
[data-testid="stModal"] [role="dialog"],
[data-testid="stDialog"],
[data-testid="stDialog"] > div,
[data-baseweb="modal"] > div {{
    background: var(--cp-surface) !important;
    background-color: var(--cp-surface) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 14px !important;
    box-shadow: var(--cp-float-shadow) !important;
}}
[role="dialog"] h1,
[role="dialog"] h2,
[role="dialog"] h3,
[role="dialog"] p,
[role="dialog"] label,
[role="dialog"] div,
[role="dialog"] span:not([data-testid="stIconMaterial"]),
[data-testid="stDialog"] h1,
[data-testid="stDialog"] h2,
[data-testid="stDialog"] p,
[data-testid="stDialog"] label {{
    color: var(--cp-text) !important;
}}
[role="dialog"] button[aria-label="Close"],
[data-testid="stDialog"] button[aria-label="Close"] {{
    color: var(--cp-muted) !important;
    background: transparent !important;
}}
[data-testid="stForm"] {{
    background: var(--cp-surface) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 14px !important;
    padding: 16px !important;
}}

/* Inputs, Radio, DateInput, Selectbox inside sidebar & dialogs (Streamlit 1.66 React Aria & BaseWeb) */
[data-testid="stTextInputRootElement"],
[data-testid="stTextAreaRootElement"],
.stTextInput > div > div,
.stTextArea > div > div,
[data-baseweb="input"],
[data-baseweb="input"] > div,
[data-baseweb="base-input"] {{
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
}}
.stTextInput input,
.stTextArea textarea {{
    background: transparent !important;
    background-color: transparent !important;
    color: var(--cp-text) !important;
    font-size: 14px !important;
}}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
[data-testid="stSelectbox"] input::placeholder {{
    color: var(--cp-muted) !important;
    opacity: 0.75 !important;
}}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stTextAreaRootElement"]:focus-within,
[data-baseweb="input"]:focus-within {{
    border-color: var(--cp-accent) !important;
    box-shadow: 0 0 0 3px var(--cp-accent-ring) !important;
}}

/* Radio buttons (stRadioOption) — no black circles in Light Mode */
[data-testid="stRadioOption"] > div > div:first-child {{
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    border: 1.5px solid var(--cp-border-strong) !important;
}}
[data-testid="stRadioOption"][data-hovered] > div > div:first-child {{
    border-color: var(--cp-accent) !important;
}}
[data-testid="stRadioOption"][data-selected] > div > div:first-child {{
    background: var(--cp-button) !important;
    background-color: var(--cp-button) !important;
    border-color: var(--cp-accent) !important;
}}
[data-testid="stRadioOption"][data-selected] > div > div:first-child > div {{
    background: var(--cp-white) !important;
    background-color: var(--cp-white) !important;
}}

/* DateInput field & spinbutton segments (stDateInputField) */
[data-testid="stDateInputField"] {{
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
    color: var(--cp-text) !important;
}}
[data-testid="stDateInputField"]:focus-within {{
    border-color: var(--cp-accent) !important;
    box-shadow: 0 0 0 3px var(--cp-accent-ring) !important;
}}
[data-testid="stDateInputField"] [role="spinbutton"],
[data-testid="stDateInputField"] [data-type="literal"],
[data-testid="stDateInputCalendarButton"],
[data-testid="stDateInputClearButton"] {{
    color: var(--cp-text) !important;
}}
[data-testid="stDateInputField"] [role="spinbutton"][data-focused] {{
    background: var(--cp-button) !important;
    background-color: var(--cp-button) !important;
    color: var(--cp-white) !important;
    border-radius: 4px !important;
}}

/* Selectbox field & Virtual Dropdown (stSelectbox / stSelectboxVirtualDropdown) */
[data-testid="stSelectbox"] [role="group"],
[data-testid="stSelectbox"] div:has(> input),
[data-testid="stSelectbox"] > div > div,
[data-testid="stSelectbox"] .react-aria-ComboBox > div,
[data-testid="stSelectbox"] .react-aria-Group,
[data-baseweb="select"] > div {{
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
    color: var(--cp-text) !important;
}}
[data-testid="stSelectbox"] [role="group"]:focus-within,
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stSelectbox"] .react-aria-ComboBox > div:focus-within {{
    border-color: var(--cp-accent) !important;
    box-shadow: 0 0 0 3px var(--cp-accent-ring) !important;
}}
[data-testid="stSelectbox"] input {{
    color: var(--cp-text) !important;
    background: transparent !important;
    background-color: transparent !important;
    -webkit-text-fill-color: var(--cp-text) !important;
}}
[data-testid="stSelectbox"] button {{
    color: var(--cp-muted) !important;
    background: transparent !important;
    background-color: transparent !important;
}}
[data-testid="stSelectboxVirtualDropdown"] {{
    background: var(--cp-surface) !important;
    background-color: var(--cp-surface) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 12px !important;
    box-shadow: var(--cp-float-shadow) !important;
    color: var(--cp-text) !important;
}}
[data-testid="stSelectboxVirtualDropdown"] [role="option"],
[data-testid="stSelectboxVirtualDropdown"] [role="option"] * {{
    color: var(--cp-text) !important;
}}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-hovered] [data-item-hl],
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused] [data-item-hl] {{
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
}}

/* Calendar Popup & Floating Overlay Portals (stDateInputCalendar) */
[data-testid="stDateInputCalendar"],
[data-testid="stDateInputHeaderPickerPopover"],
[data-testid="stDateInputQuickSelectPopover"],
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="tooltip"],
[data-baseweb="tooltip"] > div,
[data-baseweb="calendar"],
[data-baseweb="menu"],
[role="listbox"] {{
    background: var(--cp-surface) !important;
    background-color: var(--cp-surface) !important;
    color: var(--cp-text) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 14px !important;
    box-shadow: var(--cp-float-shadow) !important;
}}
[data-testid="stDateInputCalendar"] header button,
[data-testid="stDateInputCalendar"] header button *,
[data-testid="stDateInputCalendar"] th,
[data-testid="stDateInputCalendar"] .react-aria-CalendarHeaderCell,
[data-testid="stDateInputCalendar"] .react-aria-CalendarCell:not([data-selected]):not([data-outside-month]),
[data-testid="stDateInputHeaderPickerPopover"] [role="option"],
[data-testid="stDateInputQuickSelectPopover"] [role="option"],
[data-baseweb="tooltip"] * {{
    color: var(--cp-text) !important;
}}
[data-testid="stDateInputCalendar"] .react-aria-CalendarCell[data-outside-month] {{
    color: var(--cp-muted) !important;
    opacity: 0.45 !important;
}}
[data-testid="stDateInputCalendar"] .react-aria-CalendarCell[data-selected] {{
    background: var(--cp-button) !important;
    background-color: var(--cp-button) !important;
    color: var(--cp-white) !important;
    border-radius: 8px !important;
}}
[data-testid="stDateInputCalendar"] .react-aria-CalendarCell[data-today]:not([data-selected]) {{
    text-decoration-color: var(--cp-accent) !important;
    font-weight: 600 !important;
}}
[data-testid="stDateInputHeaderPickerPopover"] [role="option"][data-hovered],
[data-testid="stDateInputHeaderPickerPopover"] [role="option"][data-focused],
[data-testid="stDateInputHeaderPickerPopover"] [role="option"][data-selected] {{
    background: var(--cp-surface-2) !important;
    background-color: var(--cp-surface-2) !important;
}}

/* Expanders & Campus map iframe */
[data-testid="stExpander"] {{
    background: var(--cp-surface) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: none !important;
}}
[data-testid="stExpander"] summary {{
    background: var(--cp-surface) !important;
    color: var(--cp-text) !important;
    font-weight: 500 !important;
    padding: 10px 14px !important;
}}
[data-testid="stExpander"] summary p {{
    color: var(--cp-text) !important;
}}
[data-testid="stExpander"] summary:hover {{
    background: var(--cp-surface-2) !important;
    color: var(--cp-accent) !important;
}}
[data-testid="stExpander"] details,
[data-testid="stExpanderDetails"] {{
    background: var(--cp-surface) !important;
    color: var(--cp-text) !important;
}}
/* React Aria checkbox indicator, distinct from the hidden native input. */
[data-testid="stCheckbox"] label {{ color: var(--cp-text) !important; }}
[data-testid="stCheckbox"] label > div:not([data-testid]) {{
    background: var(--cp-surface) !important;
    border-color: var(--cp-border-strong) !important;
}}
[data-testid="stCheckbox"] label[data-selected] > div:not([data-testid]) {{
    background: var(--cp-button) !important;
    border-color: var(--cp-button) !important;
}}
[data-testid="stCheckbox"] label[data-selected] > div:not([data-testid]) svg {{
    stroke: var(--cp-white) !important;
}}
[data-testid="stCheckbox"] label[data-focus-visible] {{
    background: var(--cp-surface-2) !important;
    outline: 2px solid var(--cp-brand);
    outline-offset: 2px;
}}
iframe {{
    background: var(--cp-surface) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 14px !important;
}}

/* Brand & Status lines in Sidebar */
.cp-brand-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 19px;
    font-weight: 600;
    color: var(--cp-text);
    padding: 4px 0 8px 0;
    letter-spacing: -0.02em;
}}
.cp-brand-icon {{
    width: 30px;
    height: 30px;
    border-radius: 8px;
    background: var(--cp-accent-soft);
    color: var(--cp-accent) !important;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.cp-brand-icon svg {{
    stroke: var(--cp-accent) !important;
}}
.cp-status-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--cp-muted);
    margin: 8px 0 6px 0;
    line-height: 1.35;
}}
.cp-status-dot {{
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--cp-accent);
    flex-shrink: 0;
}}
.cp-today-line {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--cp-muted);
    padding: 6px 0;
    font-variant-numeric: tabular-nums;
}}
.cp-today-line strong {{
    color: var(--cp-text);
    font-weight: 600;
}}
.repo-pill {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--cp-surface-2);
    border: 1px solid var(--cp-border);
    border-radius: 999px;
    padding: 6px 12px;
    margin: 4px 0 12px 0;
    max-width: 100%;
    overflow: hidden;
    transition: border-color 160ms ease;
}}
.repo-pill:hover {{
    border-color: var(--cp-accent);
}}
.repo-pill a {{
    color: var(--cp-text) !important;
    text-decoration: none !important;
    font-family: var(--cp-font-mono);
    font-size: 12.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    flex: 1;
}}
.repo-pill a:hover {{
    color: var(--cp-accent) !important;
}}

/* Deadline Card — radius 14px, 3px left urgency stripe, clean hierarchy */
.dl-card {{
    background: var(--cp-surface-2);
    border: 1px solid var(--cp-border);
    border-left: 3px solid var(--cp-border-strong);
    border-radius: 14px;
    padding: 12px 14px;
    margin: 8px 0 4px 0;
    transition: border-color 180ms ease, transform 180ms ease;
}}
.dl-card:hover {{
    transform: translateY(-1px);
}}
.dl-card.dl-critical {{
    border-left-color: var(--cp-err-fg);
}}
.dl-card.dl-high {{
    border-left-color: var(--cp-accent);
}}
.dl-card.dl-normal {{
    border-left-color: var(--cp-border-strong);
}}
.dl-course {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--cp-muted);
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.dl-title {{
    font-size: 14.5px;
    font-weight: 600;
    color: var(--cp-text);
    line-height: 1.38;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 8px;
}}
.dl-footer {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 12.5px;
    color: var(--cp-muted);
    font-variant-numeric: tabular-nums;
}}
.dl-date {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--cp-muted);
}}
.dl-chip {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}}
.dl-chip.chip-critical {{
    background: var(--cp-err-bg);
    color: var(--cp-err-fg);
}}
.dl-chip.chip-high {{
    background: var(--cp-accent-soft);
    color: var(--cp-accent);
}}
.dl-chip.chip-normal {{
    background: var(--cp-surface);
    color: var(--cp-muted);
    border: 1px solid var(--cp-border);
}}

/* Empty Chat Hero State */
.hero-box {{
    text-align: center;
    padding: 36px 20px 20px 20px;
    margin: 8px auto 12px auto;
}}
.hero-logo-badge {{
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: var(--cp-accent-soft);
    border: 1px solid var(--cp-border);
    color: var(--cp-accent);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 14px;
}}
.hero-title {{
    font-size: 24px;
    font-weight: 600;
    color: var(--cp-text);
    letter-spacing: -0.02em;
    margin-bottom: 6px;
}}
.hero-sub {{
    font-size: 14.5px;
    color: var(--cp-muted);
    max-width: 520px;
    margin: 0 auto;
}}

/* LIVE / DEMO pill badges (ONLY place where green / orange are used) */
.mode-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-variant-numeric: tabular-nums;
}}
.mode-pill .mode-dot {{
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: currentColor;
}}
.mode-pill.mode-live {{
    background: var(--cp-live-bg);
    color: var(--cp-live-fg) !important;
}}
.mode-pill.mode-demo {{
    background: var(--cp-demo-bg);
    color: var(--cp-demo-fg) !important;
}}

/* Agent trace step cards */
.trace-header-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 6px 0 10px 0;
    border-bottom: 1px solid var(--cp-border);
    margin-bottom: 10px;
    font-size: 13px;
    color: var(--cp-muted);
}}
.trace-step-card {{
    background: var(--cp-surface-2);
    border: 1px solid var(--cp-border);
    border-radius: 10px;
    padding: 10px 12px;
    margin: 8px 0;
}}
.trace-step-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
}}
.trace-step-name {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--cp-font-mono);
    font-size: 13px;
    font-weight: 600;
    color: var(--cp-text);
}}
.trace-step-meta {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--cp-muted);
    font-variant-numeric: tabular-nums;
}}

/* Pulse loading indicator & Error card */
@keyframes cpPulse {{
    0%, 100% {{ opacity: 0.45; transform: scale(0.98); }}
    50% {{ opacity: 1; transform: scale(1.02); }}
}}
.cp-loading-card {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: var(--cp-surface);
    border: 1px solid var(--cp-border);
    border-radius: 14px;
    color: var(--cp-muted);
    font-size: 14px;
}}
.cp-loading-icon {{
    color: var(--cp-accent);
    display: inline-flex;
    animation: cpPulse 1.4s ease-in-out infinite;
}}
.cp-error-card {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    background: var(--cp-err-bg);
    border: 1px solid var(--cp-err-fg);
    border-radius: 14px;
    color: var(--cp-text);
    margin: 8px 0;
}}
.cp-error-icon {{
    color: var(--cp-err-fg);
    display: inline-flex;
    margin-top: 2px;
    flex-shrink: 0;
}}
.cp-error-title {{
    font-size: 14.5px;
    font-weight: 600;
    color: var(--cp-text);
    margin-bottom: 2px;
}}
.cp-error-desc {{
    font-size: 13.5px;
    color: var(--cp-muted);
}}

@media (max-width: 768px) {{
    [data-testid="stMainBlockContainer"],
    [data-testid="stBottomBlockContainer"] {{
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }}
    .hero-title {{
        font-size: 20px;
    }}
}}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }}
}}

/* Stable controls and uniform motion, including portalled dialogs. */
[data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] {{ visibility: visible !important; opacity: 1 !important; pointer-events: auto !important; z-index: 1001; }}
[data-testid="stHeader"] {{ pointer-events: auto; }}
.cp-brand-row {{ font-family: Manrope, var(--cp-font-sans); font-weight: 600; letter-spacing: -.02em; color: var(--cp-text); }}
.cp-brand-icon, .hero-logo-badge {{ color: var(--cp-brand); background: transparent; box-shadow: none; border: none; }}
.cp-brand-icon svg {{ width:32px; height:32px; }}
.cp-status-row {{ align-items:flex-start; min-width:0; line-height:1.5; }}
.st-key-deadline_header [data-testid="stHorizontalBlock"] {{ align-items:center !important; flex-wrap:nowrap !important; }}
.st-key-deadline_header [data-testid="stColumn"] {{ min-width:0 !important; }}
.st-key-deadline_header [data-testid="stElementContainer"] {{ margin:0 !important; height:36px !important; }}
.st-key-deadline_header [data-testid="stMarkdownContainer"], .st-key-deadline_header [data-testid="stMarkdownContainer"] > div {{ height:36px !important; margin:0 !important; display:flex; align-items:center; }}
.mode-demo {{ border:1px solid var(--cp-muted); background:transparent; color:var(--cp-muted); }}
.dl-card.dl-critical, .dl-card.dl-high {{ border-left-color:var(--cp-danger); }}
.dl-card.dl-medium {{ border-left-color:var(--cp-warn); }}
.dl-card.dl-normal {{ border-left-color:var(--cp-success); }}
.dl-chip.chip-high {{ background:var(--cp-err-bg); color:var(--cp-err-fg); }}
.dl-chip.chip-medium {{ background:var(--cp-warn-bg); color:var(--cp-warn-fg); }}
.dl-chip.chip-normal {{ background:var(--cp-live-bg); color:var(--cp-live-fg); }}
[data-testid="stChatInput"] {{ border-radius:20px !important; }}
[data-testid="stChatInput"]:focus-within {{ border-color:var(--cp-brand) !important; box-shadow:0 0 0 2px var(--cp-accent-ring) !important; }}
[data-testid="stBottom"]::before {{ background:var(--cp-bg); }}
button, summary, [role="button"], [role="radio"], [data-testid="stRadio"] label {{
    transition:transform 120ms cubic-bezier(.2,.8,.2,1), background-color 150ms, border-color 150ms, box-shadow 150ms, opacity 150ms !important;
}}
button:hover, summary:hover, [role="button"]:hover, [role="radio"]:hover {{ transform:translateY(-1px) !important; border-color:var(--cp-hover) !important; }}
button:active, summary:active, [role="button"]:active, [role="radio"]:active {{ transform:scale(.96) !important; transition-duration:90ms !important; }}
button:focus-visible, summary:focus-visible, [role="button"]:focus-visible, [role="radio"]:focus-visible {{ outline:2px solid var(--cp-brand) !important; outline-offset:2px !important; }}
[data-testid="stSidebar"] {{ transition:transform 220ms cubic-bezier(.4,0,.2,1), margin-left 220ms cubic-bezier(.4,0,.2,1), width 220ms cubic-bezier(.4,0,.2,1) !important; }}
@media (prefers-reduced-motion: reduce) {{
    button, summary, [role="button"], [role="radio"], .dl-card {{ transform:none !important; }}
    [data-testid="stSidebar"] {{ transition:none !important; }}
}}
</style>"""
    st.markdown(css, unsafe_allow_html=True)


apply_theme = inject_theme
