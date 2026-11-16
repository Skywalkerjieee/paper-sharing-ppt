#!/usr/bin/env python3
"""Stamp a bottom-right page number on every slide after the first.

The number is chrome, not content: 14 pt, muted grey, aligned to the body's
right margin.  `check_deck.py` recognises it and exempts it from the 18 pt body
minimum, while still requiring the section label to stay at 18-30 pt.

The script is idempotent: running it twice updates the existing number instead
of stacking a second one.

Usage
-----
    python add_page_numbers.py build/deck.pptx
    python add_page_numbers.py build/deck.pptx -o build/deck-numbered.pptx
    python add_page_numbers.py build/deck.pptx --format "{n}" --size 12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt

NAME = "page-number"
GREY = RGBColor(0x7F, 0x7F, 0x7F)
LATIN = "Times New Roman"
EA = "宋体"


def _typefaces(rpr) -> None:
    for tag in ("latin", "ea", "cs"):
        for el in rpr.findall(qn(f"a:{tag}")):
            rpr.remove(el)
    for tag, face in (("latin", LATIN), ("ea", EA), ("cs", LATIN)):
        el = rpr.makeelement(qn(f"a:{tag}"), {"typeface": face})
        rpr.append(el)


def _style(run, size_pt: float) -> None:
    run.font.size = Pt(size_pt)
    run.font.bold = False
    run.font.color.rgb = GREY
    run.font.name = LATIN  # sets <a:latin>
    rpr = run._r.get_or_add_rPr()
    rpr.set("lang", "en-US")
    _typefaces(rpr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Add bottom-right page numbers to a deck.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("pptx", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--format", default="{n} / {total}", help="text template (default '{n} / {total}')")
    ap.add_argument("--size", type=float, default=14.0)
    ap.add_argument("--inset-cm", type=float, default=0.6)
    ap.add_argument("--skip-first", action="store_true", default=True)
    ap.add_argument("--include-first", dest="skip_first", action="store_false")
    args = ap.parse_args(argv)

    src = args.pptx
    if not src.exists():
        sys.exit(f"error: not found: {src}")
    deck = Presentation(src)
    w_cm, h_cm = deck.slide_width / 360000, deck.slide_height / 360000
    total = len(deck.slides)
    box_w, box_h = 3.0, args.size * 0.045 + 0.25
    left = Cm(w_cm - args.inset_cm - box_w)
    top = Cm(h_cm - args.inset_cm - box_h)

    added = updated = 0
    for idx, slide in enumerate(deck.slides, 1):
        if args.skip_first and idx == 1:
            continue
        existing = next((s for s in slide.shapes if s.name == NAME), None)
        if existing is not None:
            shape = existing
            updated += 1
        else:
            shape = slide.shapes.add_textbox(left, top, Cm(box_w), Cm(box_h))
            shape.name = NAME
            added += 1
        tf = shape.text_frame
        tf.word_wrap = False
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.BOTTOM
        para = tf.paragraphs[0]
        para.alignment = PP_ALIGN.RIGHT
        for run in list(para.runs):
            run._r.getparent().remove(run._r)
        run = para.add_run()
        run.text = args.format.format(n=idx, total=total)
        _style(run, args.size)

    dst = args.out or src
    deck.save(dst)
    print(f"[page-numbers] {dst}: added {added}, updated {updated}, slides {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
