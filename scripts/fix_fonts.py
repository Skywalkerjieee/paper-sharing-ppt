#!/usr/bin/env python3
"""Force the paper-sharing font contract onto an existing .pptx.

Why this exists
---------------
Most PPTX builders expose one `fontFace` per run and write only `<a:latin>`.
PowerPoint then draws Chinese characters with the theme's East Asian font and
Latin characters with the run's Latin font.  A deck built with
`fontFace: "SimSun"` therefore renders English in SimSun as well, and a deck
built with `fontFace: "Times New Roman"` can render Chinese in Calibri.

The contract is per run and needs three typefaces: `<a:latin>` for Latin
letters, digits and ASCII punctuation, `<a:ea>` for CJK characters, `<a:cs>`
for complex scripts.  PowerPoint resolves every character against the matching
typeface, so a single run may contain both languages and no run splitting is
required.

This script rewrites every text run in the deck, so it works no matter which
library produced the file, and it is idempotent.

Usage
-----
    python fix_fonts.py deck.pptx                 # rewrite in place (+ .before-fonts.pptx backup)
    python fix_fonts.py deck.pptx -o fixed.pptx   # write a new file
    python fix_fonts.py deck.pptx --check         # report only, exit 1 if off-contract
    python fix_fonts.py deck.pptx --min-size 18   # also raise explicit sizes below 18 pt

Python 3.8+, standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

CJK_RANGES = (
    (0x2E80, 0x2EFF), (0x3000, 0x303F), (0x3040, 0x30FF), (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF), (0xAC00, 0xD7AF), (0xF900, 0xFAFF), (0xFE30, 0xFE4F),
    (0xFF00, 0xFFEF), (0x20000, 0x2FA1F),
)

TEXT_PART_RE = re.compile(
    r"^ppt/(slides/slide\d+\.xml|notesSlides/notesSlide\d+\.xml"
    r"|slideMasters/[^/]+\.xml|slideLayouts/[^/]+\.xml"
    r"|handoutMasters/[^/]+\.xml|theme/theme\d+\.xml)$"
)

RUN_RE = re.compile(r"<a:(?:r|fld)\b[^>]*>.*?</a:(?:r|fld)>", re.S)
T_RE = re.compile(r"<a:t\b[^>]*>(.*?)</a:t>", re.S)
RPR_RE = re.compile(r"<a:rPr\b(?P<attrs>[^>]*?)(?:/>|>(?P<inner>.*?)</a:rPr>)", re.S)
DEFAULT_RPR_RE = re.compile(
    r"<a:(?P<tag>defRPr|endParaRPr)\b(?P<attrs>[^>]*?)(?:/>|>(?P<inner>.*?)</a:\1>)", re.S
)
TYPEFACE_RE = re.compile(r"<a:(?:latin|ea|cs)\b[^>]*/>")
TAIL_TAGS = ("<a:sym", "<a:hlinkClick", "<a:hlinkMouseOver", "<a:rtl", "<a:extLst")
STRIP_TAGS_RE = re.compile(r"<[^>]+>")


def has_cjk(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in CJK_RANGES):
            return True
    return False


def _tagged(name: str, attrs: str, inner: str) -> str:
    return f"<a:{name}{attrs}>{inner}</a:{name}>"


def _rebuild(name: str, attrs: str, inner: str, cfg: dict, lang: str) -> str:
    """Rewrite one rPr-like tag with the contract's typefaces and language."""
    attrs = re.sub(r'\s+lang="[^"]*"', "", attrs)
    attrs = re.sub(r'\s+altLang="[^"]*"', "", attrs)
    if cfg["min_size"]:
        m = re.search(r'\bsz="(\d+)"', attrs)
        minimum = int(round(cfg["min_size"] * 100))
        if m and int(m.group(1)) < minimum:
            attrs = attrs.replace(m.group(0), f'sz="{minimum}"')
    lang_attr = f' lang="{lang}"'
    if lang == "zh-CN":
        lang_attr += ' altLang="en-US"'
    # keep everything except the typeface children, which we re-add in order
    inner = TYPEFACE_RE.sub("", inner or "")
    block = (
        f'<a:latin typeface="{cfg["latin"]}"/>'
        f'<a:ea typeface="{cfg["ea"]}"/>'
        f'<a:cs typeface="{cfg["latin"]}"/>'
    )
    # latin/ea/cs must precede sym/hlinkClick/hlinkMouseOver/rtl/extLst
    positions = [inner.find(t) for t in TAIL_TAGS if inner.find(t) != -1]
    at = min(positions) if positions else len(inner)
    inner = inner[:at] + block + inner[at:]
    return f"<a:{name}{lang_attr}{attrs}>{inner}</a:{name}>"


def rewrite_runs(xml: str, cfg: dict) -> tuple[str, dict]:
    stats = {"runs": 0, "cjk_runs": 0, "resized": 0, "no_rpr": 0}

    def run_repl(m: re.Match) -> str:
        body = m.group(0)
        text_m = T_RE.search(body)
        plain = STRIP_TAGS_RE.sub("", text_m.group(1)) if text_m else ""
        lang = "zh-CN" if has_cjk(plain) else "en-US"
        stats["runs"] += 1
        stats["cjk_runs"] += lang == "zh-CN"

        rpr = RPR_RE.search(body)
        if rpr is None:
            stats["no_rpr"] += 1
            head = body.index(">") + 1
            return body[:head] + _rebuild("rPr", "", "", cfg, lang) + body[head:]
        old_top = rpr.group(0)
        new_top = _rebuild("rPr", rpr.group("attrs") or "", rpr.group("inner") or "", cfg, lang)
        if cfg["min_size"]:
            a = re.search(r'\bsz="(\d+)"', old_top)
            b = re.search(r'\bsz="(\d+)"', new_top)
            if a and b and a.group(1) != b.group(1):
                stats["resized"] += 1
        return body.replace(old_top, new_top, 1)

    xml = RUN_RE.sub(run_repl, xml)

    def defaults_repl(m: re.Match) -> str:
        return _rebuild(
            m.group("tag"), m.group("attrs") or "", m.group("inner") or "", cfg, "zh-CN"
        )

    xml = DEFAULT_RPR_RE.sub(defaults_repl, xml)
    return xml, stats


def rewrite_theme(xml: str, cfg: dict) -> str:
    block = (
        f'<a:latin typeface="{cfg["latin"]}"/><a:ea typeface="{cfg["ea"]}"/>'
        f'<a:cs typeface="{cfg["latin"]}"/>'
    )
    for kind in ("majorFont", "minorFont"):
        xml = re.sub(rf"<a:{kind}\b[^>]*>.*?</a:{kind}>", _tagged(kind, "", block), xml, flags=re.S)
        xml = re.sub(rf"<a:{kind}\b[^>]*/>", _tagged(kind, "", block), xml)
    return xml


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Enforce per-run latin/ea/cs typefaces on a .pptx.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("pptx", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="write here instead of in place")
    ap.add_argument("--latin", default="Times New Roman")
    ap.add_argument("--ea", default="宋体", help="East Asian typeface (default 宋体)")
    ap.add_argument("--min-size", type=float, default=0.0,
                    help="clamp explicit run sizes below this point size")
    ap.add_argument("--check", action="store_true", help="report deviations, change nothing")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    args = ap.parse_args(argv)

    src = args.pptx
    if not src.exists():
        sys.exit(f"error: not found: {src}")
    dst = args.out or src
    cfg = {"latin": args.latin, "ea": args.ea, "min_size": args.min_size}

    with zipfile.ZipFile(src) as zin:
        entries = [(info, zin.read(info.filename)) for info in zin.infolist()]

    report = {
        "file": str(src), "runs": 0, "cjk_runs": 0, "resized": 0, "no_rpr": 0,
        "changed_parts": [], "deviations": [],
    }
    new_blobs: dict[str, bytes] = {}
    for info, blob in entries:
        name = info.filename
        if not name.endswith(".xml") or not TEXT_PART_RE.match(name):
            continue
        try:
            xml = blob.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "/theme/" in name:
            fixed = rewrite_theme(xml, cfg)
        else:
            fixed, stats = rewrite_runs(xml, cfg)
            for key in ("runs", "cjk_runs", "resized", "no_rpr"):
                report[key] += stats[key]
        if fixed != xml:
            report["changed_parts"].append(name)
            report["deviations"].append(name)
            new_blobs[name] = fixed.encode("utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[{'check' if args.check else 'fix'}] {src}")
        print(f"  text runs scanned: {report['runs']}  (containing Chinese: {report['cjk_runs']})")
        print(f"  runs without explicit rPr: {report['no_rpr']}")
        print(f"  parts to change: {len(report['changed_parts'])}")
        if report["resized"]:
            print(f"  runs enlarged to {args.min_size:g} pt: {report['resized']}")
        for name in report["changed_parts"][:15]:
            print(f"    - {name}")

    if args.check:
        return 1 if report["changed_parts"] else 0
    if not new_blobs:
        return 0

    tmp = dst.with_name(dst.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, blob in entries:
            zout.writestr(info, new_blobs.get(info.filename, blob))
    if dst == src:
        shutil.copyfile(src, src.with_name(src.stem + ".before-fonts.pptx"))
    tmp.replace(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
