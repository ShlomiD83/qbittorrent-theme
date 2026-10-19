"""Pack source/ into Onyx.qbtheme (a Qt binary resource bundle).

qBittorrent registers the bundle with QResource::registerResource(file, "/uitheme"),
i.e. it maps the bundle's root to :/uitheme itself -- so the files must be stored
at the bundle root (no qresource prefix), otherwise they end up at :/uitheme/uitheme/.

Needs Qt 6's resource compiler (rcc). It is looked up in this order:
  1. the QBT_RCC environment variable (full path to rcc / rcc.exe)
  2. rcc or pyside6-rcc on PATH
  3. the rcc shipped inside an installed PySide6 package
     (pip install PySide6-Essentials)

Run:  python tools/build_theme.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source"
OUTPUT = ROOT / "Onyx.qbtheme"
QRC = SOURCE / "resources.qrc"


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


def main():
    count = write_qrc()
    rcc = find_rcc()
    # zlib only (no zstd) so every Qt 6 build of qBittorrent can read the bundle
    cmd = rcc + ["--binary", "--no-zstd", "--compress-algo", "zlib", "-o", str(OUTPUT), str(QRC)]
    subprocess.run(cmd, check=True, cwd=SOURCE)
    data = OUTPUT.read_bytes()
    if data[:4] != b"qres":
        sys.exit("rcc did not produce a binary resource file")
    verify()
    print(f"packed {count} files -> {OUTPUT} ({len(data) // 1024} KiB)")


def verify():
    """Mount the bundle the way qBittorrent does and check the files resolve (needs PySide6)."""
    try:
        from PySide6.QtCore import QFile, QResource
    except ImportError:
        return
    if not QResource.registerResource(str(OUTPUT), "/uitheme"):
        sys.exit("built bundle could not be registered")
    for name in ("stylesheet.qss", "config.json", "icons/filter-all.svg", "ui/chevron-down.svg"):
        if not QFile.exists(f":/uitheme/{name}"):
            sys.exit(f"bundle is missing :/uitheme/{name}")
    QResource.unregisterResource(str(OUTPUT), "/uitheme")


if __name__ == "__main__":
    main()
