#!/usr/bin/env python3
"""Mechanical gate for a paper-sharing deck: everything that does not need eyes.

Rendering a deck and staring at it catches composition problems; it is a poor
tool for "is 14 pt hiding in a table cell" or "is this picture stretched by 3%".
This script checks every rule that is decidable from the file itself and prints
one line per finding, so the visual pass can focus on layout and meaning.

Requires: python-pptx, Pillow.

Usage
-----
    python check_deck.py deck.pptx
    python check_deck.py deck.pptx --json report.json
    python check_deck.py deck.pptx --min-pt 18 --margin-cm 1.2

Exit code 0 = no errors, 1 = at least one error (warnings alone still exit 0).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from pptx import Presentation

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
EMU_CM = 360000.0
EXPECTED_W = 12192000
EXPECTED_H = 6858000
SECTION_LABELS = {
    "Title", "Abstract", "Introduction", "Related Works", "Related Work",
    "Method", "Methods", "Experiments", "Experiment", "Results",
    "Conclusion", "Conclusions", "Abstract & Introduction",
}
CJK_FONTS = {"宋体", "SimSun", "SimSun-ExtB", "NSimSun"}
LATIN_FONT = "Times New Roman"


class Findings:
    def __init__(self, limit: int = 250):
        self.items: list[dict] = []
        self.limit = limit

    def add(self, level: str, slide: int | None, check: str, detail: str):
        if len(self.items) >= self.limit:
            return
        self.items.append({"level": level, "slide": slide, "check": check, "detail": detail})

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "error"]

    @property
    def warnings(self):
        return [i for i in self.items if i["level"] == "warn"]


def cm(value) -> float:
    return (value or 0) / EMU_CM


def walk(shapes):
    """Every shape once, descending into groups (python-pptx repeats table cells)."""
    for shape in shapes:
        yield shape
        if shape.shape_type == 6 and hasattr(shape, "shapes"):
            yield from walk(shape.shapes)


def shape_runs(shape):
    """All runs of a shape, including table cells."""
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        for para in shape.text_frame.paragraphs:
            yield from para.runs
    if getattr(shape, "has_table", False) and shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                for para in cell.text_frame.paragraphs:
                    yield from para.runs


def shape_text(shape) -> str:
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        return shape.text_frame.text or ""
    if getattr(shape, "has_table", False) and shape.has_table:
        return "\n".join(cell.text for row in shape.table.rows for cell in row.cells)
    return ""


def typefaces(run) -> tuple[str | None, str | None]:
    rpr = run._r.find(f"{{{NS_A}}}rPr")
    if rpr is None:
        return None, None
    latin = rpr.find(f"{{{NS_A}}}latin")
    ea = rpr.find(f"{{{NS_A}}}ea")
    return (
        latin.get("typeface") if latin is not None else None,
        ea.get("typeface") if ea is not None else None,
    )


def effective_size(run, default: float = 18.0) -> float:
    if run.font.size is not None:
        return run.font.size.pt
    para = run._r.getparent()
    if para is not None:
        ppr = para.find(f"{{{NS_A}}}pPr")
        if ppr is not None:
            d = ppr.find(f"{{{NS_A}}}defRPr")
            if d is not None and d.get("sz"):
                return int(d.get("sz")) / 100.0
    return default


def ink_offset(img) -> tuple[float, float]:
    mask = img.convert("L").point(lambda v: 255 if v < 250 else 0)
    box = mask.getbbox()
    if box is None:
        return 0.0, 0.0
    w, h = img.size
    return (
        ((box[0] + box[2]) / 2 - w / 2) / w,
        ((box[1] + box[3]) / 2 - h / 2) / h,
    )


def is_page_number(shape, text: str, h_cm: float) -> bool:
    """Bottom-corner chrome such as '7' or '7 / 24', allowed below 18 pt."""
    stripped = text.strip()
    if shape.name.lower().startswith(("page", "pagenum", "页码")):
        return True
    return bool(re.fullmatch(r"\d{1,3}(\s*/\s*\d{1,3})?", stripped)) and cm(shape.top) > h_cm * 0.88


def check(args) -> Findings:
    f = Findings(args.max_findings)
    deck = Presentation(args.pptx)
    w_cm, h_cm = cm(deck.slide_width), cm(deck.slide_height)

    if abs(deck.slide_width - EXPECTED_W) > 2000 or abs(deck.slide_height - EXPECTED_H) > 2000:
        f.add("error", None, "canvas",
              f"slide size is {w_cm:.3f} x {h_cm:.3f} cm, expected 33.867 x 19.050 cm")

    total = len(deck.slides)
    if total > args.max_slides:
        f.add("error", None, "slide-count", f"{total} slides, limit is {args.max_slides}")

    labels: list[tuple[int, object, str]] = []
    for idx, slide in enumerate(deck.slides, 1):
        all_shapes = list(walk(slide.shapes))
        text_shapes = []
        page_number_found = False
        # the top band belongs to the corner label, so body text may hang closer
        # to the top edge there as long as it does not sit under the label
        label_rects = [
            (cm(s.left), cm(s.left) + cm(s.width))
            for s in all_shapes
            if getattr(s, "has_text_frame", False) and shape_text(s).strip() in SECTION_LABELS
            and cm(s.top) < h_cm * 0.2
        ]
        for shape in all_shapes:
            text = shape_text(shape)
            if not text.strip():
                continue
            text_shapes.append(shape)

            # ---- fonts and sizes, aggregated per shape -------------------
            bad_latin: Counter = Counter()
            bad_ea = 0
            small: Counter = Counter()
            runs = 0
            chrome = is_page_number(shape, text, h_cm)
            page_number_found = page_number_found or chrome
            for run in shape_runs(shape):
                if not (run.text or "").strip():
                    continue
                runs += 1
                latin, ea = typefaces(run)
                if latin != LATIN_FONT:
                    bad_latin[latin] += 1
                if ea not in CJK_FONTS:
                    bad_ea += 1
                size = effective_size(run)
                floor = args.chrome_min_pt if chrome else args.min_pt
                if size < floor - 1e-6:
                    small[size] += 1
            if bad_latin:
                found = ", ".join(f"{v!r} x{n}" for v, n in bad_latin.most_common(3))
                f.add("error", idx, "font",
                      f"{shape.name}: latin typeface {found}, expected {LATIN_FONT!r} "
                      f"({runs} run(s), sample {text.strip()[:18]!r})")
            if bad_ea:
                f.add("error", idx, "font",
                      f"{shape.name}: {bad_ea}/{runs} run(s) have no 宋体 East Asian typeface "
                      f"(sample {text.strip()[:18]!r})")
            if small:
                found = ", ".join(f"{v:g} pt x{n}" for v, n in small.most_common(3))
                f.add("error", idx, "font-size",
                      f"{shape.name}: {found}, minimum is "
                      f"{args.chrome_min_pt if chrome else args.min_pt:g} pt "
                      f"(sample {text.strip()[:18]!r})")

            # ---- literal bullets -----------------------------------------
            paras = (shape.text_frame.paragraphs
                     if getattr(shape, "has_text_frame", False) else [])
            for para in paras:
                ptext = "".join(r.text for r in para.runs)
                if ptext.lstrip().startswith(("- ", "• ", "· ", "* ")):
                    f.add("warn", idx, "bullet",
                          f"{shape.name}: literal bullet at line start: {ptext[:24]!r}")

            # ---- margins -------------------------------------------------
            left, top = cm(shape.left), cm(shape.top)
            right, bottom = left + cm(shape.width), top + cm(shape.height)
            label = text.strip() in SECTION_LABELS
            inset = args.label_margin_cm if (label or chrome) else args.margin_cm
            gaps = {
                "left": left,
                "top": top,
                "right": w_cm - right,
                "bottom": h_cm - bottom,
            }
            if (
                not label and not chrome
                and args.top_margin_cm <= gaps["top"] < args.margin_cm
                and not any(a < right and b > left for a, b in label_rects)
            ):
                gaps["top"] = args.margin_cm  # hangs in the label band, clear of it
            side, gap = min(gaps.items(), key=lambda kv: kv[1])
            if gap < inset - 0.01:
                f.add("warn" if label else "error", idx, "margin",
                      f"{shape.name}: content within {gap:.2f} cm of the {side} edge "
                      f"(needs {inset:g} cm)")

            # ---- rough overflow, only where it would actually collide -----
            box_w = cm(shape.width)
            if box_w > 0 and not chrome:
                need = 0.0
                for para in paras:
                    para_text = "".join(r.text for r in para.runs)
                    if not para_text.strip():
                        continue
                    size = max([effective_size(r) for r in para.runs] or [0]) or args.min_pt
                    em_cm = size * 0.03528
                    width_cm = sum(
                        em_cm if ord(ch) > 0x2E7F else em_cm * 0.52
                        for ch in "".join(r.text for r in para.runs)
                    )
                    lines = max(1, math.ceil(width_cm / max(box_w - 0.2, 0.5)))
                    need += lines * size * 1.25 * 0.03528
                avail = cm(shape.height)
                spill = need - avail
                if spill > max(0.3, avail * 0.03):
                    obstacles = [
                        cm(o.top) for o in all_shapes
                        if o is not shape
                        and cm(o.top) > top + avail - 0.15
                        and min(o.left + o.width, shape.left + shape.width) > max(o.left, shape.left) + EMU_CM * 0.5
                    ]
                    clearance = (min(obstacles) if obstacles else h_cm - args.margin_cm) - (top + avail)
                    if spill > clearance - 0.2:
                        f.add("warn", idx, "overflow",
                              f"{shape.name}: text needs about {need:.1f} cm, box is {avail:.1f} cm, "
                              f"and only {max(0.0, clearance):.1f} cm is free below")

        # ---- section label ------------------------------------------------
        label_shape = None
        for s in text_shapes:
            if shape_text(s).strip() in SECTION_LABELS and cm(s.top) < h_cm * 0.2:
                label_shape = s
                labels.append((idx, s, shape_text(s).strip()))
                break
        if label_shape is None:
            f.add("error", idx, "section-label",
                  "no section label found in the top fifth of the slide")
        else:
            size = max((effective_size(r) for r in shape_runs(label_shape)), default=0)
            if not args.min_pt - 1e-6 <= size <= 30.01:
                f.add("error", idx, "section-label",
                      f"section label is {size:g} pt; keep it between {args.min_pt:g} and 30 pt")

        # ---- page number ----------------------------------------------------
        if idx > 1 and args.require_page_numbers and not page_number_found:
            f.add("error", idx, "page-number",
                  "no page number in the bottom band; run scripts/add_page_numbers.py")

        # ---- speaker notes ------------------------------------------------
        notes = ""
        if slide.has_notes_slide:
            notes = (slide.notes_slide.notes_text_frame.text or "").strip()
        if len(notes) < args.min_notes:
            f.add("error" if args.require_notes else "warn", idx, "notes",
                  f"speaker notes are {len(notes)} characters (minimum {args.min_notes})")

        # ---- pictures ------------------------------------------------------
        for pic in [s for s in walk(slide.shapes) if s.shape_type == 13]:
            pw, ph = cm(pic.width), cm(pic.height)
            if pw <= 0 or ph <= 0:
                continue
            left, top = cm(pic.left), cm(pic.top)
            gap = min(left, top, w_cm - left - pw, h_cm - top - ph)
            if gap < args.margin_cm - 0.01:
                f.add("error", idx, "margin",
                      f"{pic.name}: picture within {gap:.2f} cm of the edge")
            img = None
            if Image is not None:
                try:
                    img = Image.open(io.BytesIO(pic.image.blob))
                except Exception:
                    img = None
            if img is not None:
                ratio = (pw / ph) / (img.width / img.height)
                if abs(ratio - 1) > 0.005:
                    f.add("error", idx, "aspect",
                          f"{pic.name}: stretched {(ratio - 1) * 100:+.1f}% "
                          f"(shape {pw:.2f}x{ph:.2f} cm, image {img.width}x{img.height} px)")
                dpi = img.width / (pw / 2.54)
                if dpi < args.min_dpi:
                    f.add("warn", idx, "resolution",
                          f"{pic.name}: {dpi:.0f} dpi at {pw:.2f} cm wide (needs {args.min_dpi:g})")
                ox, oy = ink_offset(img)
                if abs(ox) > 0.02 or abs(oy) > 0.02:
                    f.add("warn", idx, "crop-centring",
                          f"{pic.name}: ink sits off-centre inside the PNG by "
                          f"{ox * 100:+.1f}% / {oy * 100:+.1f}% - re-crop with crop_pdf.py")
            off = (left + pw / 2) - w_cm / 2
            if abs(off) < 3.0 and abs(off) > args.centre_tol_cm:
                f.add("warn", idx, "centring",
                      f"{pic.name}: centre is {off:+.2f} cm from the slide centre "
                      f"(tolerance {args.centre_tol_cm:g} cm); place with "
                      f"left = (slide_width - width) / 2")

        # ---- text-on-text overlap -----------------------------------------
        for i in range(len(text_shapes)):
            for j in range(i + 1, len(text_shapes)):
                a, b = text_shapes[i], text_shapes[j]
                ix = min(a.left + a.width, b.left + b.width) - max(a.left, b.left)
                iy = min(a.top + a.height, b.top + b.height) - max(a.top, b.top)
                if ix > 0 and iy > 0 and (ix / EMU_CM) * (iy / EMU_CM) > 0.2:
                    f.add("error", idx, "overlap",
                          f"{a.name} overlaps {b.name} by "
                          f"{(ix / EMU_CM) * (iy / EMU_CM):.2f} cm2")

    # section labels must agree on corner, offset and size within a section
    by_section: dict[str, list] = {}
    for idx, shape, text in labels:
        by_section.setdefault(text, []).append((idx, shape))
    for text, group in by_section.items():
        if len(group) < 2:
            continue
        corners = {
            "left" if cm(s.left) + cm(s.width) / 2 < w_cm / 2 else "right"
            for _, s in group
        }
        tops = {round(cm(s.top), 1) for _, s in group}
        sizes = {
            round(max((effective_size(r) for r in shape_runs(s)), default=0))
            for _, s in group
        }
        where = [i for i, _ in group]
        if len(corners) > 1:
            f.add("warn", None, "section-label",
                  f"{text!r}: corner alternates across slides {where}")
        if len(tops) > 1:
            f.add("warn", None, "section-label",
                  f"{text!r}: label top varies {sorted(tops)} cm across slides {where}")
        if len(sizes) > 1:
            f.add("warn", None, "section-label",
                  f"{text!r}: label size varies {sorted(sizes)} pt across slides {where}")
    return f


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Check a paper-sharing deck against the mechanical part of the contract.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("pptx", type=Path)
    ap.add_argument("--json", type=Path, help="also write findings here as JSON")
    ap.add_argument("--min-pt", type=float, default=18.0)
    ap.add_argument("--max-slides", type=int, default=30)
    ap.add_argument("--margin-cm", type=float, default=1.2)
    ap.add_argument("--top-margin-cm", type=float, default=0.8,
                    help="top inset allowed for body text hanging in the label band")
    ap.add_argument("--label-margin-cm", type=float, default=0.4)
    ap.add_argument("--min-dpi", type=float, default=220)
    ap.add_argument("--centre-tol-cm", type=float, default=0.3)
    ap.add_argument("--min-notes", type=int, default=60)
    ap.add_argument("--allow-missing-notes", dest="require_notes", action="store_false", default=True)
    ap.add_argument("--chrome-min-pt", type=float, default=12.0,
                    help="minimum size for page numbers and other bottom-band chrome")
    ap.add_argument("--allow-missing-page-numbers", dest="require_page_numbers",
                    action="store_false", default=True)
    ap.add_argument("--max-findings", type=int, default=250)
    args = ap.parse_args(argv)

    if not args.pptx.exists():
        sys.exit(f"error: not found: {args.pptx}")

    findings = check(args)
    for item in findings.items:
        where = f"slide {item['slide']}" if item["slide"] else "deck"
        print(f"{item['level'].upper():5s} {where:>9s}  [{item['check']}] {item['detail']}")
    print(
        f"\n{len(findings.errors)} error(s), {len(findings.warnings)} warning(s), "
        f"{len(findings.items)} finding(s)"
    )
    if args.json:
        args.json.write_text(json.dumps(findings.items, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if findings.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
