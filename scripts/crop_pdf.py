#!/usr/bin/env python3
"""Deterministic figure / display-equation cropper for paper-sharing decks.

The failure mode this script removes: cropping a rendered PDF page by eye, so the
PNG keeps asymmetric white space, bleeds the neighbouring column, or clips a
superscript.  Every crop here is derived from the PDF's own text geometry, is
clipped to its text column, and is finally re-padded symmetrically around the
ink so that a centred picture shows a centred equation.

Requirements: Python 3.8+, Pillow, and poppler tools on PATH
(`pdftoppm`, `pdftotext`, `pdfinfo`).  On Windows, TeX Live ships them.

Examples
--------
One equation by its visible text::

    python crop_pdf.py --pdf paper.pdf --page 3 --text "L = 1 N" \
        --out figures/eq1.png --manifest figures/eq1.json

A figure by an approximate rectangle in PDF points (origin top-left)::

    python crop_pdf.py --pdf paper.pdf --page 4 --rect 90,210,300,430 \
        --column full --pad 2 --out figures/fig1.png

A batch described by a JSON job file::

    python crop_pdf.py --jobs figures/jobs.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

# --------------------------------------------------------------------------- #
# external tools
# --------------------------------------------------------------------------- #

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        sys.exit(
            f"error: `{name}` not found on PATH. Install poppler-utils "
            "(Windows: TeX Live or poppler-windows; macOS: brew install poppler; "
            "Linux: apt install poppler-utils) and retry."
        )
    return path


def _run(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=_CREATE_NO_WINDOW,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{args[0]} failed ({proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    return proc.stdout.decode("utf-8", "replace")


def page_size(pdf: Path, page: int) -> tuple[float, float]:
    out = _run([_tool("pdfinfo"), "-f", str(page), "-l", str(page), str(pdf)])
    for m in re.finditer(r"Page\s+(\d+)\s+size:\s+([\d.]+) x ([\d.]+) pts", out):
        if int(m.group(1)) == page:
            return float(m.group(2)), float(m.group(3))
    m = re.search(r"Page size:\s+([\d.]+) x ([\d.]+) pts", out)
    if not m:
        raise RuntimeError(f"cannot read page size for page {page}")
    return float(m.group(1)), float(m.group(2))


# --------------------------------------------------------------------------- #
# text geometry
# --------------------------------------------------------------------------- #

_WORD_RE = re.compile(
    r'<word xMin="([\d.-]+)" yMin="([\d.-]+)" xMax="([\d.-]+)" yMax="([\d.-]+)">(.*?)</word>',
    re.S,
)


class Word:
    __slots__ = ("text", "x0", "y0", "x1", "y1")

    def __init__(self, text: str, x0: float, y0: float, x1: float, y1: float):
        self.text = text
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    def rect(self) -> tuple[float, float, float, float]:
        return self.x0, self.y0, self.x1, self.y1


def read_words(pdf: Path, page: int) -> list[Word]:
    out = _run(
        [
            _tool("pdftotext"),
            "-f", str(page), "-l", str(page),
            "-bbox", "-enc", "UTF-8",
            str(pdf), "-",
        ]
    )
    words = []
    for m in _WORD_RE.finditer(out):
        text = (
            m.group(5)
            .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'")
        )
        words.append(Word(text, *(float(m.group(i)) for i in range(1, 5))))
    return words


def group_lines(words: list[Word], tol: float = 2.0) -> list[list[Word]]:
    """Group words into visual lines by vertical overlap."""
    lines: list[list[Word]] = []
    for w in sorted(words, key=lambda w: (w.y0, w.x0)):
        for line in lines:
            if abs(line[0].cy - w.cy) <= tol + 0.25 * (w.y1 - w.y0):
                line.append(w)
                break
        else:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w.x0)
    lines.sort(key=lambda line: line[0].y0)
    return lines


def find_text(words: list[Word], needle: str) -> tuple[float, float, float, float]:
    """Locate `needle` on the page and return the union bbox of the matched words.

    Whitespace is ignored on both sides, so a needle copied from a visual PDF
    page (where spaces are unreliable, especially in maths) still matches.
    """
    target = re.sub(r"\s+", "", needle)
    if not target:
        raise ValueError("empty --text")

    for line in group_lines(words):
        joined_parts, offsets, pos = [], [], 0
        for w in line:
            piece = re.sub(r"\s+", "", w.text)
            if not piece:
                continue
            offsets.append((pos, pos + len(piece), w))
            joined_parts.append(piece)
            pos += len(piece)
        joined = "".join(joined_parts)
        start = joined.find(target)
        while start != -1:
            end = start + len(target)
            hits = [w for (a, b, w) in offsets if a < end and b > start]
            if hits:
                return (
                    min(w.x0 for w in hits), min(w.y0 for w in hits),
                    max(w.x1 for w in hits), max(w.y1 for w in hits),
                )
            start = joined.find(target, start + 1)
    raise ValueError(f"text not found on page: {needle!r}")


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #

def expand(rect, dx: float, dy: float | None = None):
    dy = dx if dy is None else dy
    return (rect[0] - dx, rect[1] - dy, rect[2] + dx, rect[3] + dy)


def intersect(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def union_all(rects):
    rects = list(rects)
    return (
        min(r[0] for r in rects), min(r[1] for r in rects),
        max(r[2] for r in rects), max(r[3] for r in rects),
    )


def overlaps(a, b, tol: float = 0.0) -> bool:
    return not (a[2] - tol <= b[0] or b[2] - tol <= a[0] or a[3] - tol <= b[1] or b[3] - tol <= a[1])


def overlap_area(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def bbox_of(words: list[Word]):
    return union_all([w.rect() for w in words])


def _best_line(lines, rect):
    """Index of the line overlapping `rect` most, or None."""
    if not lines:
        return None
    areas = [overlap_area(bbox_of(line), rect) for line in lines]
    k = max(range(len(lines)), key=lambda i: areas[i])
    return k if areas[k] > 0 else None


def detect_columns(words: list[Word], rect, page_w: float) -> list[tuple[float, float]]:
    """Return x-ranges of the text columns in the vertical band of `rect`.

    A gutter is the widest uncovered x-gap near the page centre with text on
    both sides.  If no such gutter exists (single-column page, or a full-width
    element), the whole text area is returned as one column.
    """
    band = [w for w in words if abs(w.cy - (rect[1] + rect[3]) / 2) < 160]
    if not band:
        return [(0.0, page_w)]
    x0 = min(w.x0 for w in band)
    x1 = max(w.x1 for w in band)
    step = 0.5
    n = int((x1 - x0) / step) + 2
    covered = [False] * n
    for w in band:
        a = max(0, int((w.x0 - x0) / step))
        b = min(n - 1, int((w.x1 - x0) / step))
        for i in range(a, b + 1):
            covered[i] = True

    gaps = []
    i = 0
    while i < n:
        if covered[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and not covered[j + 1]:
            j += 1
        start, end = x0 + i * step, x0 + j * step
        if end - start >= 8 and start < page_w * 0.7 and end > page_w * 0.3:
            gaps.append((end - start, start, end))
        i = j + 1

    if not gaps:
        return [(x0, x1)]
    _, gap_start, gap_end = max(gaps)
    left = [w for w in band if w.x1 <= gap_start + 1]
    right = [w for w in band if w.x0 >= gap_end - 1]
    if len(left) < 5 or len(right) < 5:
        return [(x0, x1)]
    return [(min(w.x0 for w in left), gap_start), (gap_end, max(w.x1 for w in right))]


def choose_column(columns, rect, mode: str):
    if mode == "full" or len(columns) == 1:
        return columns[0][0], columns[-1][1]
    if mode == "left":
        return columns[0]
    if mode == "right":
        return columns[-1]
    # auto: the column holding the rect centre
    cx = (rect[0] + rect[2]) / 2
    best = min(columns, key=lambda c: 0 if c[0] <= cx <= c[1] else min(abs(cx - c[0]), abs(cx - c[1])))
    if not (best[0] - 2 <= cx <= best[1] + 2):
        raise SystemExit(
            f"error: the given rect centre x={cx:.1f}pt is not inside any text column; "
            "pass --column left|right|full explicitly."
        )
    return best


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

def render_page(pdf: Path, page: int, dpi: int, cache_dir: Path) -> tuple[Image.Image, float]:
    """Render one page to PNG via poppler; returns (image, px_per_pt)."""
    prefix = cache_dir / f"p{page}-{dpi}"
    png = prefix.with_suffix(".png")
    if not png.exists():
        _run([
            _tool("pdftoppm"), "-png", "-singlefile", "-r", str(dpi),
            "-f", str(page), "-l", str(page), str(pdf), str(prefix),
        ])
    return Image.open(png).convert("RGB"), dpi / 72.0


def ink_bbox(img: Image.Image, threshold: int = 250):
    """Bounding box of non-near-white pixels, or None for a blank image."""
    mask = img.convert("L").point(lambda v: 255 if v < threshold else 0)
    return mask.getbbox()


def _runs(flags: list[bool]) -> list[list[int]]:
    runs: list[list[int]] = []
    for i, flag in enumerate(flags):
        if flag:
            if runs and runs[-1][1] == i - 1:
                runs[-1][1] = i
            else:
                runs.append([i, i])
    return runs


def _has_ink_per_line(mask: Image.Image) -> list[bool]:
    width, height = mask.size
    data = mask.tobytes()
    return [any(data[y * width:(y + 1) * width]) for y in range(height)]


def ink_trim_with_edge_bands(mask: Image.Image, gap_px: int):
    """BBox of the ink after dropping edge bands that are clearly separate.

    A slightly loose crop often keeps a sliver of the paragraph above, or the
    caption below, separated from the target by a wide blank band.  Dropping
    only *edge* runs separated by at least `gap_px` removes that junk while
    leaving the target's own rows intact (their gaps are much smaller).
    """
    box = mask.getbbox()
    if box is None:
        return None
    left, top, right, bottom = box

    rows = _runs(_has_ink_per_line(mask.crop((left, top, right, bottom))))
    rows = [[a + top, b + top] for a, b in rows]
    while len(rows) > 1 and rows[1][0] - rows[0][1] - 1 >= gap_px:
        rows.pop(0)
    while len(rows) > 1 and rows[-1][0] - rows[-2][1] - 1 >= gap_px:
        rows.pop()
    top, bottom = rows[0][0], rows[-1][1] + 1

    column_mask = mask.crop((left, top, right, bottom)).transpose(Image.ROTATE_90)
    cols = _runs(_has_ink_per_line(column_mask))
    cols = [[a + left, b + left] for a, b in cols]
    while len(cols) > 1 and cols[1][0] - cols[0][1] - 1 >= gap_px:
        cols.pop(0)
    while len(cols) > 1 and cols[-1][0] - cols[-2][1] - 1 >= gap_px:
        cols.pop()
    left, right = cols[0][0], cols[-1][1] + 1
    return (left, top, right, bottom)


def crop_with_symmetric_padding(page_img, rect, scale, pad_px, band_gap_px):
    """Crop `rect` (points), drop separated edge bands, centre the ink with equal padding."""
    box = (
        max(0, int(math.floor(rect[0] * scale))),
        max(0, int(math.floor(rect[1] * scale))),
        min(page_img.width, int(math.ceil(rect[2] * scale))),
        min(page_img.height, int(math.ceil(rect[3] * scale))),
    )
    if box[2] - box[0] < 8 or box[3] - box[1] < 8:
        raise ValueError("crop rectangle is too small")
    crop = page_img.crop(box)
    mask = crop.convert("L").point(lambda v: 255 if v < 250 else 0)
    if mask.getbbox() is None:
        raise ValueError("crop contains no visible ink; check --rect / --text")

    ink = ink_trim_with_edge_bands(mask, band_gap_px) if band_gap_px > 0 else mask.getbbox()
    clipped = ink[0] <= 0 or ink[1] <= 0 or ink[2] >= crop.width or ink[3] >= crop.height
    core = crop.crop(ink)
    out = Image.new("RGB", (core.width + 2 * pad_px, core.height + 2 * pad_px), "white")
    out.paste(core, (pad_px, pad_px))
    return out, box, ink, clipped


# --------------------------------------------------------------------------- #
# one crop
# --------------------------------------------------------------------------- #

def crop_one(spec: dict, pdf: Path, cache: Path) -> dict:
    page = int(spec["page"])
    dpi = int(spec.get("dpi") or spec.get("_dpi") or 300)
    pad = float(spec.get("pad", 6))
    grow = float(spec.get("grow", 1.0))
    column_mode = spec.get("column", "auto")
    out_path = Path(spec["out"])

    page_w, page_h = page_size(pdf, page)
    words = read_words(pdf, page)

    if spec.get("text"):
        rect = find_text(words, spec["text"])
        mode = spec.get("mode") or "line"
    elif spec.get("rect"):
        rect = tuple(float(v) for v in spec["rect"])
        mode = spec.get("mode") or "exact"
    else:
        raise ValueError("each crop needs either `text` or `rect`")
    rows = max(1, int(spec.get("rows", 1)))

    columns = detect_columns(words, expand(rect, grow), page_w)
    col_x0, col_x1 = choose_column(columns, rect, column_mode)

    if mode == "line":
        # Snap to one display row: useful for single-row equations, where the
        # located text is only a fragment of the row.  Multi-row equations must
        # be given as a rect instead, because their glyph rows interleave.
        lines = group_lines([w for w in words if col_x0 - 0.5 <= w.cx <= col_x1 + 0.5])
        k = _best_line(lines, rect)
        if k is not None:
            k0 = max(0, k - (rows - 1) // 2)
            k1 = min(len(lines) - 1, k0 + rows - 1)
            k0 = max(0, k1 - rows + 1)
            rect = bbox_of([w for line in lines[k0:k1 + 1] for w in line])

    # clamp to the column so the neighbouring column can never bleed in
    clamped = intersect(expand(rect, grow), (col_x0, 0.0, col_x1, page_h))

    page_img, scale = render_page(pdf, page, dpi, cache)
    img, box_px, ink_px, ink_at_border = crop_with_symmetric_padding(
        page_img, clamped, scale, max(1, round(pad * scale)),
        band_gap_px=0 if spec.get("keep_bands") else max(1, round(6.0 * scale)),
    )
    # In line mode the box is the row bbox itself, so ink at the border is expected.
    clipped = ink_at_border and mode == "exact"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)

    # words that survived inside the crop
    inside_words = [w for w in words if overlaps(w.rect(), clamped, tol=1.0) and w.text.strip()]
    heights = sorted(w.y1 - w.y0 for w in inside_words)
    median_h = heights[len(heights) // 2] if heights else 0.0
    record = {
        "id": spec.get("id") or out_path.stem,
        "page": page,
        "out": str(out_path),
        "page_size_pt": [page_w, page_h],
        "columns_pt": [[round(a, 1), round(b, 1)] for a, b in columns],
        "column_pt": [round(col_x0, 1), round(col_x1, 1)],
        "request_pt": [round(v, 1) for v in (spec.get("rect") or [])] if spec.get("rect") else None,
        "crop_pt": [round(v, 1) for v in clamped],
        "mode": mode,
        "rows": rows,
        "pad_pt": pad,
        "dpi": dpi,
        "px": [img.width, img.height],
        "ink_px": [ink_px[0] + 0, ink_px[1] + 0, ink_px[2] - ink_px[0], ink_px[3] - ink_px[1]],
        "size_cm": [round(img.width / dpi * 2.54, 2), round(img.height / dpi * 2.54, 2)],
        # median glyph-box height of the text inside: divide by ~0.9 for the
        # source point size, then multiply by (placed_cm / size_cm[0]) to get
        # the on-slide point size.
        "median_word_height_pt": round(median_h, 2),
        "words_inside": [w.text for w in inside_words][:12],
        "ink_clipped": clipped,
    }
    warnings = []
    if clipped:
        warnings.append(
            "ink touches the crop border: enlarge --grow, or the content extends "
            "outside the detected column (pass --column full)."
        )
    if warnings:
        record["warning"] = " ".join(warnings)
    return record


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Crop figures and display equations from a paper PDF deterministically.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--jobs", type=Path, help="JSON file with a `crops` list")
    ap.add_argument("--pdf", type=Path)
    ap.add_argument("--page", type=int)
    ap.add_argument("--rect", help="x0,y0,x1,y1 in PDF points, origin top-left")
    ap.add_argument("--text", help="visible text of the equation/line to locate")
    ap.add_argument("--mode", default=None, choices=["line", "exact"],
                    help="line: snap to one display row (default with --text); "
                         "exact: crop the given rect, trimmed to its ink "
                         "(default with --rect)")
    ap.add_argument("--rows", type=int, default=1,
                    help="how many visual lines to include, centred on the located line (default 1)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--manifest", type=Path, help="write the crop manifest here")
    ap.add_argument("--grow", type=float, default=1.0, help="pt of slack before measuring (default 4)")
    ap.add_argument("--pad", type=float, default=6.0, help="uniform white padding in pt (default 6)")
    ap.add_argument("--dpi", type=int, default=300, help="render resolution (default 300)")
    ap.add_argument("--column", default="auto", choices=["auto", "left", "right", "full"])
    ap.add_argument("--keep-render", action="store_true", help="keep the cached full-page PNGs")
    ap.add_argument("--keep-bands", action="store_true",
                    help="do not drop separated edge bands (use when a figure's "
                         "legend or panel is intentionally detached)")
    args = ap.parse_args(argv)

    if args.jobs:
        job = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
        pdf = Path(job["pdf"])
        if not pdf.is_absolute():
            pdf = (Path(args.jobs).parent / pdf).resolve()
        specs = job["crops"]
        defaults = {k: job[k] for k in ("dpi", "pad", "grow", "column", "mode") if k in job}
        base = Path(args.jobs).resolve().parent
        for spec in specs:
            for key, value in defaults.items():
                spec.setdefault(key, value)
            out = Path(spec["out"])
            spec["out"] = str(out if out.is_absolute() else base / out)
        manifest_arg = args.manifest or job.get("manifest")
        if manifest_arg:
            mp = Path(manifest_arg)
            manifest_path = mp if mp.is_absolute() else base / mp
        else:
            manifest_path = Path(args.jobs).with_suffix(".out.json")
    else:
        if not (args.pdf and args.page and args.out):
            ap.error("either --jobs, or --pdf/--page/--out together")
        pdf = args.pdf
        specs = [{
            "page": args.page,
            "rect": [float(v) for v in args.rect.split(",")] if args.rect else None,
            "text": args.text,
            "out": str(args.out),
            "grow": args.grow, "pad": args.pad, "dpi": args.dpi, "column": args.column,
            "mode": args.mode, "rows": args.rows, "keep_bands": args.keep_bands,
        }]
        manifest_path = Path(args.manifest) if args.manifest else args.out.with_suffix(".json")

    if not pdf.exists():
        sys.exit(f"error: PDF not found: {pdf}")

    cache = Path(specs[0]["out"]).parent / ".crop-cache"
    cache.mkdir(parents=True, exist_ok=True)
    records, failed = [], 0
    try:
        for i, spec in enumerate(specs, 1):
            try:
                rec = crop_one(spec, pdf, cache)
                records.append(rec)
                flag = "  [WARN ink_clipped]" if rec.get("warning") else ""
                print(
                    f"[{i}/{len(specs)}] {rec['id']}: p{rec['page']} "
                    f"{rec['size_cm'][0]}x{rec['size_cm'][1]}cm at {rec['dpi']}dpi -> {rec['out']}{flag}"
                )
            except Exception as exc:  # keep the batch going
                failed += 1
                print(f"[{i}/{len(specs)}] {spec.get('id', '?')}: FAILED - {exc}", file=sys.stderr)
    finally:
        if not args.keep_render:
            shutil.rmtree(cache, ignore_errors=True)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"pdf": str(pdf), "crops": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"manifest: {manifest_path}")
    print(
        "place each image with width = size_cm[0] * scale and height unchanged; "
        "effective dpi at that width = 300 by construction."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

