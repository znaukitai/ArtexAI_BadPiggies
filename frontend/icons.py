"""Linear 24x24 SVG icons and neutral avatar data URIs for CampusPulse UI."""

from __future__ import annotations

import base64

_SVG_ATTRS = (
    'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round"'
)

ICONS: dict[str, str] = {
    "brand_pulse": (
        f'<svg {_SVG_ATTRS} width="20" height="20">'
        '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>'
        "</svg>"
    ),
    "calendar": (
        f'<svg {_SVG_ATTRS} width="16" height="16">'
        '<rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/>'
        '<line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/>'
        "</svg>"
    ),
    "clock": (
        f'<svg {_SVG_ATTRS} width="14" height="14">'
        '<circle cx="12" cy="12" r="9"/>'
        '<polyline points="12 7 12 12 15 15"/>'
        "</svg>"
    ),
    "alert_triangle": (
        f'<svg {_SVG_ATTRS} width="14" height="14">'
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
        "</svg>"
    ),
    "check_circle": (
        f'<svg {_SVG_ATTRS} width="14" height="14">'
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/>'
        "</svg>"
    ),
    "github": (
        f'<svg {_SVG_ATTRS} width="15" height="15">'
        '<line x1="6" y1="3" x2="6" y2="15"/>'
        '<circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/>'
        '<path d="M18 9a9 9 0 0 1-9 9"/>'
        "</svg>"
    ),
    "map_pin": (
        f'<svg {_SVG_ATTRS} width="16" height="16">'
        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
        '<circle cx="12" cy="10" r="3"/>'
        "</svg>"
    ),
    "plus": (
        f'<svg {_SVG_ATTRS} width="18" height="18">'
        '<line x1="12" y1="5" x2="12" y2="19"/>'
        '<line x1="5" y1="12" x2="19" y2="12"/>'
        "</svg>"
    ),
    "sparkles": (
        f'<svg {_SVG_ATTRS} width="16" height="16">'
        '<path d="M12 3l1.9 5.8a2 2 0 0 0 1.3 1.3L21 12l-5.8 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.8a2 2 0 0 0-1.3-1.3L3 12l5.8-1.9a2 2 0 0 0 1.3-1.3L12 3z"/>'
        "</svg>"
    ),
    "book_open": (
        f'<svg {_SVG_ATTRS} width="16" height="16">'
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
        "</svg>"
    ),
    "trash": (
        f'<svg {_SVG_ATTRS} width="14" height="14">'
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        "</svg>"
    ),
}


def get_icon(name: str) -> str:
    """Return inline SVG markup for the requested icon name."""
    return ICONS.get(name, ICONS["sparkles"])


def _svg_data_uri(svg_markup: str) -> str:
    encoded = base64.b64encode(svg_markup.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def get_avatar_uri(role: str, theme: str = "dark") -> str:
    """Return neutral SVG data URI for user or assistant chat avatar."""
    is_dark = theme == "dark"
    bg = "#1A2232" if is_dark else "#F4F4F5"
    border = "#2D3748" if is_dark else "#E4E4E7"
    fg_user = "#9AA4B5" if is_dark else "#52525B"
    fg_assistant = "#35C3CF" if is_dark else "#0B7C87"

    if role == "user":
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
            f'<rect x="1" y="1" width="30" height="30" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>'
            f'<g transform="translate(4,4)" fill="none" stroke="{fg_user}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
            f'<circle cx="12" cy="7" r="4"/>'
            f"</g></svg>"
        )
    else:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
            f'<rect x="1" y="1" width="30" height="30" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>'
            f'<g transform="translate(4,4)" fill="none" stroke="{fg_assistant}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>'
            f"</g></svg>"
        )
    return _svg_data_uri(svg)
