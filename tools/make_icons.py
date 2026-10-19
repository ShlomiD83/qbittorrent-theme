"""Generate the Onyx icon set for qBittorrent.

Every qBittorrent icon id is mapped either to a Material Icons (Round) glyph from
tools/material-icons/round (Apache-2.0, see tools/material-icons/LICENSE) or to a
hand-drawn SVG, and written to source/icons/<id>.svg in its palette colour.
UI glyphs used by the stylesheet (chevrons, check marks, ...) go to source/ui/.

Run:  python tools/make_icons.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATERIAL = HERE / "material-icons" / "round"
ICONS = HERE.parent / "source" / "icons"
UI = HERE.parent / "source" / "ui"

# Palette (Apple system colours, as used by the concept)
WHITE = "#FFFFFF"
LIGHT = "#EDEDED"   # general menu / dialog glyphs
MUTED = "#C5C5C5"   # properties tab bar, search glyph
GREY = "#8E8E93"
YELLOW = "#FFCC00"
GREEN = "#4CD964"
BLUE = "#56CCF2"
PINK = "#FF2D55"
ORANGE = "#FF9500"
RED = "#FF3B30"
PURPLE = "#BF5AF2"
TEAL = "#64D2FF"
INDIGO = "#7D7AFF"


def material(name):
    svg = (MATERIAL / f"{name}.svg").read_text(encoding="utf-8")
    return re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)


def wrap(inner, color, transform=None):
    body = f'<g transform="{transform}">{inner}</g>' if transform else inner
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
            f'fill="{color}">{body}</svg>\n')


def stroke(d, width=2.0):
    return (f'<path d="{d}" fill="none" stroke="currentColor" stroke-width="{width}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')


def custom(inner, color):
    # currentColor is resolved here because Qt's SVG renderer has no CSS colour context
    return wrap(inner.replace("currentColor", color), color)


CUSTOM = {
    # queue controls: bar + chevron, and wide solid triangles (as in the concept toolbar)
    "go-top": '<rect x="5" y="3.6" width="14" height="2.2" rx="1.1"/>' + stroke("M7 16.2l5-5 5 5", 2.3),
    "go-bottom": '<rect x="5" y="18.2" width="14" height="2.2" rx="1.1"/>' + stroke("M7 7.8l5 5 5-5", 2.3),
    "go-up": '<path d="M2.6 16.4 12 6.9l9.4 9.5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>',
    "go-down": '<path d="M2.6 7.6h18.8L12 17.1z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>',
    # thin download arrow standing on a base line
    "downloading": stroke("M12 3.2v12.3M7.2 10.9l4.8 4.8 4.8-4.8", 2.0) + '<rect x="5" y="19.2" width="14" height="2" rx="1"/>',
    "download": stroke("M12 3.2v12.3M7.2 10.9l4.8 4.8 4.8-4.8", 2.0) + '<rect x="5" y="19.2" width="14" height="2" rx="1"/>',
    # vertical equaliser sliders (Trackers tab)
    "trackers": (stroke("M5 3.5v17M9.7 3.5v17M14.3 3.5v17M19 3.5v17", 1.7)
                 + '<rect x="3" y="6" width="4" height="3" rx="1"/><rect x="7.7" y="12.5" width="4" height="3" rx="1"/>'
                 + '<rect x="12.3" y="5" width="4" height="3" rx="1"/><rect x="17" y="10.5" width="4" height="3" rx="1"/>'),
    # horseshoe magnet
    "torrent-magnet": ('<path d="M5 3h4.4v8.2a2.6 2.6 0 0 0 5.2 0V3H19v8.4a7 7 0 0 1-14 0z"/>'
                       '<rect x="5" y="3" width="4.4" height="3.2" fill="#FF6B6B"/><rect x="14.6" y="3" width="4.4" height="3.2" fill="#FF6B6B"/>'),
}

ICON_MAP = {
    # --- main toolbar (white, as in the concept)
    "insert-link": ("link", WHITE),
    "list-add": ("note_add", WHITE),
    "list-remove": ("delete", WHITE),
    "torrent-start": ("play_arrow", WHITE),
    "torrent-stop": ("pause", WHITE),
    "torrent-start-forced": ("fast_forward", WHITE),
    "pause-session": ("pause_circle_outline", WHITE),
    "go-top": ("@custom", WHITE),
    "go-up": ("@custom", WHITE),
    "go-down": ("@custom", WHITE),
    "go-bottom": ("@custom", WHITE),
    "configure": ("settings", WHITE),
    "object-locked": ("lock", YELLOW),
    "torrent-creator": ("edit_note", WHITE),
    # --- search box
    "edit-find": ("search", "#C3C3C3"),
    "edit-clear": ("backspace", MUTED),
    # --- status filters (sidebar)
    "filter-all": ("folder", YELLOW),
    "downloading": ("@custom", GREEN),
    "upload": ("cloud_upload", BLUE),
    "checked-completed": ("check", GREEN),
    "stopped": ("pause", PINK),
    "paused": ("pause_circle", PINK),
    "filter-active": ("star", ORANGE),
    "filter-inactive": ("star_border", ORANGE),
    "filter-stalled": ("hourglass_bottom", INDIGO),
    "stalledUP": ("arrow_circle_up", BLUE),
    "stalledDL": ("arrow_circle_down", GREEN),
    "force-recheck": ("autorenew", PURPLE),
    "set-location": ("drive_file_move", TEAL),
    "error": ("priority_high", RED),
    "queued": ("schedule", "#A1A1A6"),
    # --- properties tab bar
    "help-about": ("settings_applications", MUTED),
    "trackers": ("@custom", MUTED),
    "peers": ("public", MUTED),
    "network-server": ("web_asset", MUTED),
    "directory": ("folder_special", MUTED),
    "chart-line": ("show_chart", MUTED),
    # --- status bar
    "connected": ("rss_feed", "#BCBCBC"),
    "firewalled": ("rss_feed", ORANGE),
    "disconnected": ("portable_wifi_off", RED),
    "slow_off": ("speed", "#FF453A"),
    "slow": ("speed", TEAL),
    "speedometer": ("speed", LIGHT),
    # --- menus, dialogs, everything else
    "application-exit": ("power_settings_new", LIGHT),
    "application-rss": ("rss_feed", ORANGE),
    "application-url": ("link", LIGHT),
    "browser-cookies": ("cookie", LIGHT),
    "dialog-warning": ("warning", YELLOW),
    "download": ("@custom", LIGHT),
    "edit-copy": ("content_copy", LIGHT),
    "edit-rename": ("drive_file_rename_outline", LIGHT),
    "fileicon": ("insert_drive_file", MUTED),
    "folder-documents": ("folder_open", MUTED),
    "folder-new": ("create_new_folder", LIGHT),
    "folder-remote": ("swap_vert", LIGHT),
    "hash": ("tag", LIGHT),
    "help-contents": ("menu_book", LIGHT),
    "ip-blocked": ("block", RED),
    "loading": ("hourglass_empty", MUTED),
    "mail-inbox": ("inbox", LIGHT),
    "name": ("label", LIGHT),
    "network-connect": ("lan", LIGHT),
    "peers-add": ("person_add", LIGHT),
    "peers-remove": ("person_remove", LIGHT),
    "plugins": ("extension", LIGHT),
    "preferences-advanced": ("tune", LIGHT),
    "preferences-bittorrent": ("hub", LIGHT),
    "preferences-desktop": ("desktop_windows", LIGHT),
    "preferences-webui": ("language", LIGHT),
    "ratio": ("donut_large", LIGHT),
    "reannounce": ("campaign", LIGHT),
    "security-high": ("verified_user", GREEN),
    "security-low": ("lock_open", ORANGE),
    "system-log-out": ("logout", LIGHT),
    "tags": ("sell", LIGHT),
    "task-complete": ("task_alt", LIGHT),
    "task-reject": ("cancel", LIGHT),
    "tracker-error": ("error", RED),
    "tracker-warning": ("warning", YELLOW),
    "trackerless": ("link_off", LIGHT),
    "view-categories": ("category", LIGHT),
    "view-preview": ("visibility", LIGHT),
    "view-refresh": ("refresh", LIGHT),
    "view-statistics": ("bar_chart", LIGHT),
    "wallet-open": ("savings", LIGHT),
    "rss_read_article": ("drafts", GREY),
    "rss_unread_article": ("mark_email_unread", ORANGE),
    "torrent-magnet": ("@custom", LIGHT),
}

# Glyphs referenced from stylesheet.qss as url(":/uitheme/ui/<name>.svg")
UI_GLYPHS = {
    "chevron-down": custom(stroke("M6.5 9.5 12 15l5.5-5.5", 2.2), "#F2F2F2"),
    "chevron-right": custom(stroke("M9.5 6.5 15 12l-5.5 5.5", 2.2), "#F2F2F2"),
    "chevron-up": custom(stroke("M6.5 14.5 12 9l5.5 5.5", 2.2), "#F2F2F2"),
    "chevron-down-muted": custom(stroke("M6.5 9.5 12 15l5.5-5.5", 2.2), "#8E8E93"),
    "chevron-right-muted": custom(stroke("M9.5 6.5 15 12l-5.5 5.5", 2.2), "#8E8E93"),
    "chevron-up-muted": custom(stroke("M6.5 14.5 12 9l5.5 5.5", 2.2), "#8E8E93"),
    "chevron-down-disabled": custom(stroke("M6.5 9.5 12 15l5.5-5.5", 2.2), "#4A4A4A"),
    "chevron-up-disabled": custom(stroke("M6.5 14.5 12 9l5.5 5.5", 2.2), "#4A4A4A"),
    "sort-down": custom(stroke("M6.5 9.5 12 15l5.5-5.5", 3.0), "#FFFFFF"),
    "sort-up": custom(stroke("M6.5 14.5 12 9l5.5 5.5", 3.0), "#FFFFFF"),
    "check": custom(stroke("M6 12.4l3.9 3.9L18 8.2", 2.6), "#FFFFFF"),
    "check-disabled": custom(stroke("M6 12.4l3.9 3.9L18 8.2", 2.6), "#6E6E73"),
    "menu-check": custom(stroke("M6 12.4l3.9 3.9L18 8.2", 2.4), "#4CD964"),
    "dash": custom('<rect x="6.5" y="10.9" width="11" height="2.2" rx="1.1"/>', "#FFFFFF"),
    "radio-dot": custom('<circle cx="12" cy="12" r="4.6"/>', "#FFFFFF"),
    "menu-radio": custom('<circle cx="12" cy="12" r="4"/>', "#4CD964"),
    "close": custom(stroke("M7.5 7.5l9 9M16.5 7.5l-9 9", 2.0), "#A1A1A6"),
    "close-hover": custom(stroke("M7.5 7.5l9 9M16.5 7.5l-9 9", 2.0), "#FFFFFF"),
    "msg-info": wrap(material("info"), "#0A84FF"),
    "msg-question": wrap(material("help_outline"), "#0A84FF"),
    "grip": custom('<circle cx="12" cy="7" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="12" cy="17" r="1.3"/>', "#3A3A3A"),
}


def main():
    ICONS.mkdir(parents=True, exist_ok=True)
    UI.mkdir(parents=True, exist_ok=True)
    for icon_id, (source, color) in ICON_MAP.items():
        svg = custom(CUSTOM[icon_id], color) if source == "@custom" else wrap(material(source), color)
        (ICONS / f"{icon_id}.svg").write_text(svg, encoding="utf-8")
    for name, svg in UI_GLYPHS.items():
        (UI / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(f"{len(ICON_MAP)} icons -> {ICONS}")
    print(f"{len(UI_GLYPHS)} ui glyphs -> {UI}")


if __name__ == "__main__":
    main()
