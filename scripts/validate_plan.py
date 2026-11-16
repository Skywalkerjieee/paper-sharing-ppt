#!/usr/bin/env python3
"""Validate the deck plan before any slide is built.

Writing the plan first is cheaper than discovering on slide 27 that the method
section cannot fit 30 slides at 18 pt.  The plan is a small JSON file:

    {
      "paper": {"title": "...", "venue": "...", "year": 2024},
      "slides": [
        {"n": 1, "section": "Title", "layout": "title", "heading": null,
         "chars": 0, "assets": ["title-block"], "notes_chars": 90},
        {"n": 2, "section": "Abstract", "layout": "prose", "heading": null,
         "chars": 380, "assets": [], "notes_chars": 120}
      ]
    }

`layout` is one of: title, prose, figure, table, formula, figure-text,
table-text.  Layouts that show a paper object must list it in `assets`.

Values are the same ones `assets/style-spec.json` records; change them there
and here together.

Usage
-----
    python validate_plan.py build/plan.json
    python validate_plan.py build/plan.json --json report.json
    python validate_plan.py --init build/plan.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SECTIONS = [
    "Title", "Abstract", "Introduction", "Related Works",
    "Method", "Experiments", "Conclusion",
]
MERGED = "Abstract & Introduction"
LAYOUTS = {"title", "prose", "figure", "table", "formula", "figure-text", "table-text"}
ASSET_LAYOUTS = {"figure", "table", "formula", "figure-text", "table-text"}

REQUIRED = {
    "Title": (1, 1),
    "Abstract": (1, 2),
    "Introduction": (2, 3),
    "Related Works": (2, 3),
    "Method": (4, 16),
    "Experiments": (3, 12),
    "Conclusion": (1, 1),
}

EXAMPLE = {
    "paper": {"title": "Paper title", "venue": "Venue", "year": 2024},
    "slides": [
        {"n": 1, "section": "Title", "layout": "title", "heading": None,
         "chars": 0, "assets": ["title-block"], "notes_chars": 90},
        {"n": 2, "section": "Abstract", "layout": "prose", "heading": None,
         "chars": 380, "assets": [], "notes_chars": 120},
        {"n": 3, "section": "Introduction", "layout": "prose", "heading": "研究背景与动机",
         "chars": 420, "assets": [], "notes_chars": 110},
        {"n": 4, "section": "Introduction", "layout": "prose", "heading": "本文贡献",
         "chars": 300, "assets": [], "notes_chars": 100},
        {"n": 5, "section": "Related Works", "layout": "prose", "heading": "现有方法",
         "chars": 400, "assets": [], "notes_chars": 110},
        {"n": 6, "section": "Related Works", "layout": "prose", "heading": "研究空白",
         "chars": 320, "assets": [], "notes_chars": 100},
        {"n": 7, "section": "Method", "layout": "figure", "heading": "整体框架",
         "chars": 80, "assets": ["arch-fig"], "notes_chars": 200},
        {"n": 8, "section": "Method", "layout": "formula", "heading": "对齐目标",
         "chars": 260, "assets": ["eq1"], "notes_chars": 160},
        {"n": 9, "section": "Method", "layout": "prose", "heading": "区分项",
         "chars": 420, "assets": [], "notes_chars": 120},
        {"n": 10, "section": "Method", "layout": "prose", "heading": "训练与推理",
         "chars": 380, "assets": [], "notes_chars": 120},
        {"n": 11, "section": "Experiments", "layout": "prose", "heading": "实验设置",
         "chars": 380, "assets": [], "notes_chars": 110},
        {"n": 12, "section": "Experiments", "layout": "table", "heading": "主实验对比",
         "chars": 120, "assets": ["tab1"], "notes_chars": 180},
        {"n": 13, "section": "Experiments", "layout": "table", "heading": "消融实验",
         "chars": 120, "assets": ["tab2"], "notes_chars": 150},
        {"n": 14, "section": "Conclusion", "layout": "prose", "heading": None,
         "chars": 300, "assets": [], "notes_chars": 110},
    ],
}


class Report:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, level: str, where: str, detail: str):
        self.items.append({"level": level, "where": where, "detail": detail})

    def errors(self):
        return [i for i in self.items if i["level"] == "error"]

    def warnings(self):
        return [i for i in self.items if i["level"] == "warn"]


def validate(plan: dict, max_slides: int, notes_min: int, warn_chars: int, max_chars: int) -> Report:
    r = Report()
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        r.add("error", "plan", "`slides` is missing or empty")
        return r

    if len(slides) > max_slides:
        r.add("error", "plan", f"{len(slides)} slides planned, limit is {max_slides}")

    order = {name: i for i, name in enumerate(SECTIONS)}
    last_section = -1
    seen: dict[str, int] = {}
    total_chars = 0

    for i, slide in enumerate(slides):
        where = f"slide {slide.get('n', i + 1)}"
        if slide.get("n") != i + 1:
            r.add("error", where, f"`n` should be {i + 1}, found {slide.get('n')!r}")
        section = slide.get("section")
        layout = slide.get("layout")
        if section not in SECTIONS and section != MERGED:
            r.add("error", where, f"unknown section {section!r}")
            continue
        if layout not in LAYOUTS:
            r.add("error", where, f"unknown layout {layout!r}")
        keys = ["Abstract", "Introduction"] if section == MERGED else [section]
        for key in keys:
            seen[key] = seen.get(key, 0) + 1
        if section != MERGED:
            idx = order[section]
            if idx < last_section:
                r.add("error", where, f"section {section!r} comes after {SECTIONS[last_section]!r}")
            last_section = max(last_section, idx)

        chars = slide.get("chars", 0)
        if not isinstance(chars, int) or chars < 0:
            r.add("error", where, "`chars` must be a non-negative integer")
        else:
            total_chars += chars
            if chars > max_chars:
                r.add("error", where, f"{chars} characters planned, a slide holds about {warn_chars}")
            elif chars > warn_chars:
                r.add("warn", where, f"{chars} characters planned, above {warn_chars}")

        assets = slide.get("assets") or []
        if layout in ASSET_LAYOUTS and not assets:
            r.add("error", where, f"layout {layout!r} needs at least one entry in `assets`")
        if layout == "prose" and assets:
            r.add("warn", where, "prose slide lists assets; use figure-text or table-text")

        notes_chars = slide.get("notes_chars", 0)
        if not isinstance(notes_chars, int) or notes_chars < notes_min:
            r.add("error", where, f"notes planned with {notes_chars} characters, minimum is {notes_min}")

    first = slides[0]
    if first.get("section") != "Title":
        r.add("error", "slide 1", "the first slide must be the Title slide")
    if first.get("layout") != "title":
        r.add("error", "slide 1", "the first slide must use layout 'title'")

    for name, (lo, hi) in REQUIRED.items():
        count = seen.get(name, 0)
        if count == 0:
            r.add("error", "plan", f"section {name!r} has no slide")
        elif count < lo:
            r.add("warn", "plan", f"section {name!r} has {count} slide(s), expected {lo}-{hi}")
        elif count > hi:
            r.add("warn", "plan", f"section {name!r} has {count} slides, expected {lo}-{hi}")
    if MERGED in {s.get("section") for s in slides}:
        r.add("warn", "plan", f"{MERGED!r} is used; it counts for both Abstract and Introduction")

    if total_chars > 30 * 450:
        r.add("warn", "plan", f"{total_chars} characters planned in total, unusually dense")

    if len(slides) > 26:
        r.add("warn", "plan", f"{len(slides)} slides leaves little room to split an overflowing slide")

    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate a paper-sharing deck plan.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("plan", type=Path, nargs="?")
    ap.add_argument("--init", type=Path, help="write a starter plan here and exit")
    ap.add_argument("--json", type=Path, help="write findings here as JSON")
    ap.add_argument("--max-slides", type=int, default=30)
    ap.add_argument("--notes-min", type=int, default=60)
    ap.add_argument("--warn-chars", type=int, default=600)
    ap.add_argument("--max-chars", type=int, default=800)
    args = ap.parse_args(argv)

    if args.init:
        args.init.parent.mkdir(parents=True, exist_ok=True)
        args.init.write_text(json.dumps(EXAMPLE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote starter plan: {args.init}")
        return 0

    if not args.plan:
        ap.error("give a plan path, or --init to create one")
    if not args.plan.exists():
        sys.exit(f"error: not found: {args.plan}")

    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"error: invalid JSON in {args.plan}: {exc}")

    report = validate(plan, args.max_slides, args.notes_min, args.warn_chars, args.max_chars)
    for item in report.items:
        print(f"{item['level'].upper():5s} {item['where']:>9s}  {item['detail']}")
    slides = len(plan.get("slides") or [])
    print(f"\n{slides} slide(s) planned, {len(report.errors())} error(s), {len(report.warnings())} warning(s)")
    if args.json:
        args.json.write_text(json.dumps(report.items, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if report.errors() else 0


if __name__ == "__main__":
    raise SystemExit(main())
