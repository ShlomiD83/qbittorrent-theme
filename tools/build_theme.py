"""Pack source/ into the theme files (Qt binary resource bundles):

  Nightseed.qbtheme              source/ as it is
  Nightseed-Alternative.qbtheme  the same source with the ALTERNATIVE changes below
  Nightseed-OLED.qbtheme         the same source with the OLED changes below
  Nightseed-Transparent.qbtheme  the same source with the TRANSPARENT changes below

qBittorrent registers a bundle with QResource::registerResource(file, "/uitheme"),
i.e. it maps the bundle's root to :/uitheme itself -- so the files must be stored
at the bundle root (no qresource prefix), otherwise they end up at :/uitheme/uitheme/.

Needs Qt 6's resource compiler (rcc). It is looked up in this order:
  1. the QBT_RCC environment variable (full path to rcc / rcc.exe)
  2. rcc or pyside6-rcc on PATH
  3. the rcc shipped inside an installed PySide6 package
     (pip install PySide6-Essentials)

Run:  python tools/build_theme.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source"
OUTPUT = ROOT / "Nightseed.qbtheme"
ALT_OUTPUT = ROOT / "Nightseed-Alternative.qbtheme"
OLED_OUTPUT = ROOT / "Nightseed-OLED.qbtheme"
TRANSPARENT_OUTPUT = ROOT / "Nightseed-Transparent.qbtheme"
QRC = SOURCE / "resources.qrc"

# --- ALTERNATIVE ------------------------------------------------------------------
# Nightseed Alternative is the same source with four differences (the README's
# "Two versions" section describes them for users):
# 1. In-cell progress bars (transfer list, file lists, preview dialog) get no chunk
#    rule, so Qt's Fusion style paints them in the colour qBittorrent passes: the
#    row's state colour once the user ticks "Make progress bars follow text colors"
#    (5.2+), else "ProgressBar" green. qBittorrent draws those bars through a
#    parentless QProgressBar, so scoping the chunk rules to bars inside another
#    widget keeps dialog progress bars exactly as in Nightseed.
# 2. State icons at the start of each transfer-list row.
# 3. A white percentage on stopped / errored bars, which now sits on a coloured fill
#    instead of Nightseed's dark grey.
# 4. Darker downloading / seeding colours. Row text and bar share one colour per
#    state, so it must keep white text readable on the bar (3.6:1 for both).
ALT_QSS = [  # (Nightseed text, Alternative text); each must occur exactly once
    ("QProgressBar::chunk {", "QWidget QProgressBar::chunk {"),
    ("QProgressBar::chunk:disabled {", "QWidget QProgressBar::chunk:disabled {"),
    ("    qproperty-iconSize: 0px 0px;", "    qproperty-iconSize: 16px 16px;"),
    ("QProgressBar:disabled {\n    color: #C7C7CC;\n}",
     "QProgressBar:disabled {\n    color: #FFFFFF;\n}\n\n"
     "QWidget QProgressBar:disabled {\n    color: #C7C7CC;\n}"),
]
ALT_ROW_COLOURS = {"#4CD964": "#279A4A", "#56CCF2": "#308CCE"}  # TransferList.* values
ALT_HEADER = ("/* Nightseed Alternative: generated from stylesheet.qss by tools/build_theme.py,\n"
              "   which lists the differences. The comments below describe Nightseed. */\n\n")

# --- OLED -------------------------------------------------------------------------
# Nightseed OLED is the same source with the near-black canvas family taken to true
# black, so those pixels switch off on an OLED screen. These colours change wherever they
# appear (stylesheet and config.json); cards, menus, controls and text stay as they are.
OLED_COLOURS = {
    "#121212": "#000000",  # the canvas: main window, dialogs, transfer list, headers, logs
    "#0F0F0F": "#000000",  # dividers, which sit a step below the canvas
    "#161616": "#040404",  # alternate rows, still 4 steps above the canvas
}
OLED_QSS = [  # (Nightseed text, OLED text); each must occur exactly once
    # The progress-bar groove is a white tint: 5% comes out #1E1E1E on the #121212 canvas,
    # but only #0D0D0D on black, where an empty bar would all but vanish. 30/255 comes out
    # #1E1E1E on black, and still sits a little lighter than selected rows and cards.
    ("    background-color: rgba(255, 255, 255, 0.05);", "    background-color: rgba(255, 255, 255, 30);"),
]
OLED_HEADER = ("/* Nightseed OLED: generated from stylesheet.qss by tools/build_theme.py,\n"
               "   which lists the differences. The comments below describe Nightseed. */\n\n")

# --- TRANSPARENT --------------------------------------------------------------------
# Nightseed Transparent is for a tool that puts a Windows backdrop (blur, Mica, Acrylic)
# behind qBittorrent's windows and extends it over the whole window: the Windhawk mod
# "Translucent Windows", or Mica For Everyone with "Extend frame into client area".
# qBittorrent and Qt pass a window's per-pixel alpha on to Windows, so this version only
# has to leave its backgrounds see-through:
# 1. The canvas (#121212) becomes transparent; every other dark grey in a background or
#    border becomes a white tint of about the same lightness step over the backdrop
#    (cards, chrome, text boxes, drop-downs, buttons, tabs, check boxes, scroll bars,
#    hover and selection fills). The build stops on any dark grey without a tint below.
# 2. Lists and the speed graph inside the details card become fully transparent:
#    translucent layers stack, so a second card-coloured layer would darken the card.
# 3. Pop-ups (menus, drop-down lists, tooltips) stay opaque: they are separate windows
#    that the mod leaves alone, so a see-through pop-up would turn black.
# Without such a tool Windows draws the see-through parts black.
TRANSPARENT_COLOURS = {
    "#0F0F0F": "rgba(0, 0, 0, 70)",
    "#121212": "transparent",
    "#161616": "rgba(255, 255, 255, 4)",
    "#1A1A1A": "rgba(255, 255, 255, 8)",
    "#1C1C1C": "rgba(255, 255, 255, 8)",
    "#1E1E1E": "rgba(255, 255, 255, 13)",
    "#1F1F1F": "rgba(255, 255, 255, 10)",
    "#222222": "rgba(255, 255, 255, 5)",
    "#232323": "rgba(255, 255, 255, 6)",
    "#242424": "rgba(255, 255, 255, 8)",
    "#252525": "rgba(255, 255, 255, 9)",
    "#262626": "rgba(255, 255, 255, 14)",
    "#282828": "rgba(255, 255, 255, 16)",
    "#2A2A2A": "rgba(255, 255, 255, 16)",
    "#2B2B2B": "rgba(255, 255, 255, 16)",
    "#2C2C2C": "rgba(255, 255, 255, 20)",
    "#2E2E2E": "rgba(255, 255, 255, 20)",
    "#333333": "rgba(255, 255, 255, 26)",
    "#363636": "rgba(255, 255, 255, 28)",
    "#383838": "rgba(255, 255, 255, 30)",
    "#3A3A3A": "rgba(255, 255, 255, 32)",
    "#3C3C3C": "rgba(255, 255, 255, 40)",
    "#3D3D3D": "rgba(255, 255, 255, 36)",
    "#404040": "rgba(255, 255, 255, 40)",
    "#4A4A4A": "rgba(255, 255, 255, 56)",
    "#575757": "rgba(255, 255, 255, 72)",
    "#6A6A6A": "rgba(255, 255, 255, 90)",
}
TRANSPARENT_POPUP = re.compile(r"^(QMenu(?=$|[\s:,])|QToolTip|(QDialog )?QComboBox QAbstractItemView)")
TRANSPARENT_CLEAR = [  # card children painted in the card colour (each must exist exactly once)
    "PropertiesWidget QAbstractItemView, PropertiesWidget QHeaderView, "
    "PropertiesWidget QHeaderView::section, PropertiesWidget QTextEdit",
    "PropertiesWidget SpeedPlotView",
]
TRANSPARENT_PROPS = re.compile(r"((?:alternate-|selection-)?background(?:-color)?|border(?:-[a-z]+)*|gridline-color)"
                               r"(\s*:\s*)([^;]*)")
TRANSPARENT_HEADER = ("/* Nightseed Transparent: generated from stylesheet.qss by tools/build_theme.py,\n"
                      "   which lists the differences. The comments below describe Nightseed. */\n\n")


def find_rcc():
    if os.environ.get("QBT_RCC"):
        return [os.environ["QBT_RCC"]]
    for name in ("rcc", "pyside6-rcc"):
        exe = shutil.which(name)
        if exe:
            return [exe]
    try:
        import PySide6  # noqa: F401
        exe = Path(PySide6.__file__).parent / ("rcc.exe" if os.name == "nt" else "Qt/libexec/rcc")
        if exe.exists():
            return [str(exe)]
    except ImportError:
        pass
    sys.exit("rcc not found: set QBT_RCC, put rcc on PATH, or `pip install PySide6-Essentials`.")


def write_qrc():
    files = ["stylesheet.qss", "config.json"]
    files += sorted(p.relative_to(SOURCE).as_posix() for p in (SOURCE / "icons").glob("*.svg"))
    files += sorted(p.relative_to(SOURCE).as_posix() for p in (SOURCE / "ui").glob("*.svg"))
    lines = ["<!DOCTYPE RCC>", '<RCC version="1.0">', '  <qresource>']
    lines += [f"    <file>{f}</file>" for f in files]
    lines += ["  </qresource>", "</RCC>", ""]
    QRC.write_text("\n".join(lines), encoding="utf-8")
    return len(files)


def make_alternative(src):
    """Turn a copy of source/ into the Alternative's source."""
    qss_path = src / "stylesheet.qss"
    qss = qss_path.read_text(encoding="utf-8")
    for old, new in ALT_QSS:
        if qss.count(old) != 1:
            sys.exit(f"Alternative build: expected {old!r} exactly once in stylesheet.qss")
        qss = qss.replace(old, new)
    qss_path.write_text(ALT_HEADER + qss, encoding="utf-8")

    cfg_path = src / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    colors = cfg["colors"]
    darkened = 0
    for key, value in list(colors.items()):
        if key.startswith("TransferList.") and value.upper() in ALT_ROW_COLOURS:
            colors[key] = ALT_ROW_COLOURS[value.upper()]
            darkened += 1
    if not darkened:
        sys.exit("Alternative build: no TransferList colours in config.json to darken")
    cfg_path.write_text(json.dumps(cfg, indent=4) + "\n", encoding="utf-8")


def make_oled(src):
    """Turn a copy of source/ into the OLED version's source."""
    qss_path = src / "stylesheet.qss"
    qss = qss_path.read_text(encoding="utf-8")
    for old, new in OLED_QSS:
        if qss.count(old) != 1:
            sys.exit(f"OLED build: expected {old!r} exactly once in stylesheet.qss")
        qss = qss.replace(old, new)
    for old, new in OLED_COLOURS.items():
        qss, n = re.subn(re.escape(old), new, qss, flags=re.IGNORECASE)
        if not n:
            sys.exit(f"OLED build: {old} does not occur in stylesheet.qss")
    qss_path.write_text(OLED_HEADER + qss, encoding="utf-8")

    cfg_path = src / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    colors = cfg["colors"]
    changed = [key for key, value in colors.items() if value.upper() in OLED_COLOURS]
    for key in changed:
        colors[key] = OLED_COLOURS[colors[key].upper()]
    if "Palette.Base" not in changed:
        sys.exit("OLED build: Palette.Base in config.json is no longer the canvas colour")
    cfg_path.write_text(json.dumps(cfg, indent=4) + "\n", encoding="utf-8")


def make_transparent(src):
    """Turn a copy of source/ into the Transparent version's source (see TRANSPARENT above)."""
    qss_path = src / "stylesheet.qss"
    qss = qss_path.read_text(encoding="utf-8")
    comments = re.compile(r"/\*.*?\*/", re.S)
    if any("{" in c or "}" in c for c in comments.findall(qss)):
        sys.exit("Transparent build: a comment in stylesheet.qss contains a brace; the rule parser can't skip it")
    clear_found = dict.fromkeys(TRANSPARENT_CLEAR, 0)
    untinted = []

    def is_popup(selector):
        hits = [bool(TRANSPARENT_POPUP.match(part.strip())) for part in selector.split(",")]
        if any(hits) and not all(hits):
            sys.exit(f"Transparent build: one rule mixes pop-up and window selectors: {selector}")
        return all(hits)

    def fix_rule(m):
        head, body = m.group(1), m.group(2)
        selector = " ".join(comments.sub("", head).split())
        if is_popup(selector):
            return m.group(0)
        clear = selector in clear_found
        if clear:
            clear_found[selector] += 1

        def fix_colour(c, prop):
            colour = c.group(0).upper()
            if clear and colour == "#1E1E1E":
                return "transparent"
            if colour in TRANSPARENT_COLOURS:
                return TRANSPARENT_COLOURS[colour]
            r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
            if r == g == b and r < 0x80:  # an opaque dark grey with no tint: would show as a solid patch
                untinted.append(f"{colour} ({prop}) in {selector}")
            return c.group(0)

        def fix_decl(d):
            prop, colon, value = d.groups()
            return prop + colon + re.sub(r"#[0-9A-Fa-f]{6}\b", lambda c: fix_colour(c, prop), value)

        parts = re.split(r"(/\*.*?\*/)", body, flags=re.S)  # leave comments inside the rule alone
        body = "".join(p if p.startswith("/*") else TRANSPARENT_PROPS.sub(fix_decl, p) for p in parts)
        return head + "{" + body + "}"

    qss = re.sub(r"([^{}]+)\{([^{}]*)\}", fix_rule, qss)
    if untinted:
        sys.exit("Transparent build: dark greys with no tint in TRANSPARENT_COLOURS:\n  " + "\n  ".join(untinted))
    for selector, n in clear_found.items():
        if n != 1:
            sys.exit(f"Transparent build: expected the rule {selector!r} exactly once, found {n}")
    qss_path.write_text(TRANSPARENT_HEADER + qss, encoding="utf-8")


def keep_source_times(variant):
    """Give the files a variant rewrote their source file's timestamp. rcc stores each file's
    modification time in the bundle, so without this every rebuild of a variant differs byte
    for byte, and the release workflow (which compares bytes) would publish a new release."""
    for path in variant.rglob("*"):
        original = SOURCE / path.relative_to(variant)
        if path.is_file() and original.is_file():
            st = original.stat()
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))


def pack(rcc, src, out):
    # zlib only (no zstd) so every Qt 6 build of qBittorrent can read the bundle
    cmd = rcc + ["--binary", "--no-zstd", "--compress-algo", "zlib", "-o", str(out), str(src / "resources.qrc")]
    subprocess.run(cmd, check=True, cwd=src)
    data = out.read_bytes()
    if data[:4] != b"qres":
        sys.exit(f"rcc did not produce a binary resource file: {out.name}")
    verify(out)
    return len(data)


def main():
    count = write_qrc()
    rcc = find_rcc()
    size = pack(rcc, SOURCE, OUTPUT)
    print(f"packed {count} files -> {OUTPUT} ({size // 1024} KiB)")
    for make, out in ((make_alternative, ALT_OUTPUT), (make_oled, OLED_OUTPUT),
                      (make_transparent, TRANSPARENT_OUTPUT)):
        with tempfile.TemporaryDirectory() as tmp:
            variant = Path(tmp) / "source"
            shutil.copytree(SOURCE, variant)
            make(variant)
            keep_source_times(variant)
            size = pack(rcc, variant, out)
        print(f"packed {count} files -> {out} ({size // 1024} KiB)")


def verify(bundle):
    """Mount the bundle the way qBittorrent does and check the files resolve (needs PySide6)."""
    try:
        from PySide6.QtCore import QFile, QResource
    except ImportError:
        return
    if not QResource.registerResource(str(bundle), "/uitheme"):
        sys.exit(f"{bundle.name} could not be registered")
    for name in ("stylesheet.qss", "config.json", "icons/filter-all.svg", "ui/chevron-down.svg"):
        if not QFile.exists(f":/uitheme/{name}"):
            sys.exit(f"{bundle.name} is missing :/uitheme/{name}")
    QResource.unregisterResource(str(bundle), "/uitheme")


if __name__ == "__main__":
    main()
