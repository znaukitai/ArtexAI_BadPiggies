"""Linear 24x24 SVG icons and neutral avatar data URIs for CampusPulse UI."""

from __future__ import annotations

import base64

_SVG_PATHS: dict[str, str] = {
    # Signature pulse motif (single broken impulse polyline)
    "logo": '<path d="M3 12h4.2l2.6-6.5 4.4 13 2.6-6.5H21"/>',
    "brand_pulse": '<path d="M3 12h4.2l2.6-6.5 4.4 13 2.6-6.5H21"/>',
    "loader": (
        '<circle cx="12" cy="12" r="9" stroke-opacity="0.25"/>'
        '<path d="M5.5 12h3l1.8-4.2 3.4 8.4 1.8-4.2h3"/>'
    ),
    "chat": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "settings": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 '
        '1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06'
        'a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06'
        'a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 '
        '1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 1 1 0 4h-.09'
        'a1.65 1.65 0 0 0-1.51 1z"/>'
    ),
    "branch": (
        '<line x1="6" y1="3" x2="6" y2="15"/>'
        '<circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/>'
        '<path d="M18 9a9 9 0 0 1-9 9"/>'
    ),
    "github": (
        '<line x1="6" y1="3" x2="6" y2="15"/>'
        '<circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/>'
        '<path d="M18 9a9 9 0 0 1-9 9"/>'
    ),
    "calendar_clock": (
        '<path d="M21 7.5V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h3.5"/>'
        '<path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h5"/>'
        '<circle cx="17.5" cy="17.5" r="4.5"/><path d="M17.5 15.5v2l1.5 1"/>'
    ),
    "calendar": (
        '<rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/>'
        '<line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/>',
    "warning": (
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
    ),
    "alert_triangle": (
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
    ),
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "check_circle": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "map": '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>',
    "map_pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "building": (
        '<rect x="4" y="2" width="16" height="20" rx="2"/>'
        '<path d="M9 22v-4h6v4"/>'
        '<path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/>'
        '<path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/>'
    ),
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "send": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "sun": (
        '<circle cx="12" cy="12" r="5"/>'
        '<line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
        '<line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>'
        '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
    ),
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    "chevron": '<polyline points="9 18 15 12 9 6"/>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "braces": '<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1"/><path d="M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1"/>',
    "tasks": '<line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><polyline points="4 6 5 7 7 5"/><polyline points="4 12 5 13 7 11"/><polyline points="4 18 5 19 7 17"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "close": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "info": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    "sparkles": '<path d="M12 3l1.9 5.8a2 2 0 0 0 1.3 1.3L21 12l-5.8 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.8a2 2 0 0 0-1.3-1.3L3 12l5.8-1.9a2 2 0 0 0 1.3-1.3L12 3z"/>',
    "book_open": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "trash": '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
}

_DEFAULT_SIZES: dict[str, int] = {
    "logo": 20,
    "brand_pulse": 20,
    "calendar": 16,
    "calendar_clock": 16,
    "clock": 14,
    "warning": 14,
    "alert_triangle": 14,
    "check": 14,
    "check_circle": 14,
    "branch": 15,
    "github": 15,
    "map": 16,
    "map_pin": 16,
    "plus": 18,
    "trash": 14,
    "wrench": 15,
    "braces": 15,
}


def icon(name: str, size: int = 18) -> str:
    """Return single-line inline SVG markup on a 24x24 grid with 1.5px rounded stroke."""
    inner = _SVG_PATHS.get(name, _SVG_PATHS["logo"])
    attrs = (
        f'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'width="{size}" height="{size}" fill="none" stroke="currentColor" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0;display:inline-block;vertical-align:middle;"'
    )
    return f"<svg {attrs}>{inner}</svg>"


def get_icon(name: str, size: int | None = None) -> str:
    """Backward-compatible helper returning inline SVG for the requested icon name."""
    resolved_size = size if size is not None else _DEFAULT_SIZES.get(name, 16)
    return icon(name, size=resolved_size)


ICONS: dict[str, str] = {k: get_icon(k) for k in _SVG_PATHS}


def _svg_data_uri(svg_markup: str) -> str:
    encoded = base64.b64encode(svg_markup.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def get_avatar_uri(role: str, theme: str = "dark") -> str:
    """Return neutral circular SVG data URI for user or assistant chat avatar."""
    is_dark = theme == "dark"
    bg = "#111827" if is_dark else "#FFFFFF"
    border = "rgba(255,255,255,0.10)" if is_dark else "#E4E4E7"
    fg_user = "#9AA4B5" if is_dark else "#52525B"
    fg_assistant = "#35C3CF" if is_dark else "#0B7C87"

    if role == "user":
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
            f'<circle cx="16" cy="16" r="15" fill="{bg}" stroke="{border}" stroke-width="1"/>'
            f'<g transform="translate(4,4)" fill="none" stroke="{fg_user}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
            f'<circle cx="12" cy="7" r="4"/>'
            f"</g></svg>"
        )
    else:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
            f'<circle cx="16" cy="16" r="15" fill="{bg}" stroke="{border}" stroke-width="1"/>'
            f'<g transform="translate(4,4)" fill="none" stroke="{fg_assistant}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M3 12h4.2l2.6-6.5 4.4 13 2.6-6.5H21"/>'
            f"</g></svg>"
        )
    return _svg_data_uri(svg)
