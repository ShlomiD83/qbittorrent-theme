"""Pack source/ into the two theme files (Qt binary resource bundles):

  Nightseed.qbtheme              source/ as it is
  Nightseed-Alternative.qbtheme  the same source with the ALTERNATIVE changes below

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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source"
OUTPUT = ROOT / "Nightseed.qbtheme"
ALT_OUTPUT = ROOT / "Nightseed-Alternative.qbtheme"
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
    with tempfile.TemporaryDirectory() as tmp:
        alt = Path(tmp) / "source"
        shutil.copytree(SOURCE, alt)
        make_alternative(alt)
        size = pack(rcc, alt, ALT_OUTPUT)
    print(f"packed {count} files -> {ALT_OUTPUT} ({size // 1024} KiB)")


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
