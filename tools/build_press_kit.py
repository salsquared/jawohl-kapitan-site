#!/usr/bin/env python3
"""Builds press/jawohl-kapitan-press-kit.zip from press/kit-src/ (stdlib only, byte-for-byte repeatable).
Run from anywhere: python3 tools/build_press_kit.py

Lines starting with TODO-COPY in the .txt sources are notes for the maintainers; they are left out of the zip.
tools/check_site.py imports kit_files() and zip_bytes() to check that the zip on disk is current."""
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "press" / "kit-src"
OUT = ROOT / "press" / "jawohl-kapitan-press-kit.zip"
DATE = (2026, 11, 21, 0, 0, 0)


def strip_notes(text):
    """The text as it goes into the zip: no TODO-COPY lines, one final newline."""
    lines = [l for l in text.splitlines() if not l.startswith("TODO-COPY")]
    return "\n".join(lines).rstrip("\n") + "\n"


def kit_files():
    """[(name in the zip, bytes)] in a fixed order."""
    out = []
    for f in sorted(p for p in SRC.rglob("*") if p.is_file()):
        data = f.read_bytes()
        if f.suffix == ".txt":
            data = strip_notes(data.decode("utf-8")).encode("utf-8")
        out.append((f.relative_to(SRC).as_posix(), data))
    return out


def zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in kit_files():
            info = zipfile.ZipInfo(name, date_time=DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return buf.getvalue()


if __name__ == "__main__":
    OUT.write_bytes(zip_bytes())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
