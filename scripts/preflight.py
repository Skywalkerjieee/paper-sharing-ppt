#!/usr/bin/env python3
"""Report whether this machine can run the paper-sharing pipeline.

Checks the two dependency groups the scripts rely on:

- Python: version, Pillow, python-pptx.
- poppler binaries: pdfinfo, pdftotext, pdftoppm (used by crop_pdf.py).

`office_render` is a DSH tool, not a binary, so it cannot be probed here: the
skill loads it with `skill('office')`. This script prints that reminder instead
of guessing.

Exit code 0 when everything needed is present, 1 otherwise. It changes nothing.

Usage
-----
    python preflight.py
    python preflight.py --json
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

MIN_PYTHON = (3, 8)
POPPLER = ("pdfinfo", "pdftotext", "pdftoppm")


def check_python() -> list[dict]:
    rows = []
    ok = sys.version_info >= MIN_PYTHON
    rows.append({
        "group": "python",
        "item": "interpreter",
        "ok": ok,
        "detail": f"{platform.python_version()} at {sys.executable}"
        + ("" if ok else f" (needs >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})"),
    })
    for module, hint in (("PIL", "pip install Pillow"), ("pptx", "pip install python-pptx")):
        try:
            imported = __import__(module)
            version = getattr(imported, "__version__", "unknown")
            rows.append({"group": "python", "item": module, "ok": True, "detail": version})
        except Exception as exc:  # noqa: BLE001 - report any import failure
            rows.append({"group": "python", "item": module, "ok": False,
                         "detail": f"{exc} ({hint})"})
    return rows


def check_poppler() -> list[dict]:
    rows = []
    for name in POPPLER:
        path = shutil.which(name)
        rows.append({
            "group": "poppler",
            "item": name,
            "ok": path is not None,
            "detail": path or "not on PATH (install poppler-utils; on Windows TeX Live ships it)",
        })
    return rows


def check_assets(skill_dir: Path) -> list[dict]:
    rows = []
    for rel in ("assets/style-spec.json", "scripts/crop_pdf.py", "scripts/check_deck.py"):
        path = skill_dir / rel
        rows.append({"group": "skill", "item": rel, "ok": path.exists(),
                     "detail": str(path) if path.exists() else f"missing: {path}"})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Check the dependencies of the paper-sharing pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    skill_dir = Path(__file__).resolve().parent.parent
    rows = check_python() + check_poppler() + check_assets(skill_dir)
    failed = [r for r in rows if not r["ok"]]

    if args.json:
        print(json.dumps({"ok": not failed, "rows": rows}, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            mark = "ok  " if row["ok"] else "MISS"
            print(f"{mark} {row['group']:7s} {row['item']:18s} {row['detail']}")
        print()
        if failed:
            print(f"{len(failed)} missing item(s). Fix those before building; "
                  "do not substitute a hand-made crop or a guessed font.")
        else:
            print("all script dependencies present.")
        print("rendering: call skill('office') and use office_render — not probed here.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
