"""Backward-compatible re-exports of CampusPulse UI theme and components."""

from __future__ import annotations

from frontend.components import (
    format_badge_html,
    open_action_dialog,
    render_deadlines,
    render_empty_state,
    render_error_card,
    render_loading_state,
    render_mode_badge,
    render_response,
)
from frontend.theme import PALETTES, apply_theme, inject_theme

__all__ = [
    "PALETTES",
    "apply_theme",
    "format_badge_html",
    "inject_theme",
    "open_action_dialog",
    "render_deadlines",
    "render_empty_state",
    "render_error_card",
    "render_loading_state",
    "render_mode_badge",
    "render_response",
]
