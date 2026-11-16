---
name: paper-sharing-ppt
description: Create Chinese lab-meeting paper-sharing PPTX decks from one selected academic paper PDF. Use when the user provides or points to a paper PDF and asks for a paper sharing presentation, literature sharing slides, seminar/group-meeting PPT, or a Chinese research paper presentation deck.
---

# Paper Sharing PPT

## Purpose

Create a source-faithful Chinese paper-sharing `.pptx` from one selected academic paper PDF for graduate group meetings. The final deck must explain the paper in a plain academic style, include presenter notes, and stay within 30 slides.

Use the PDF as the source of truth. Do not invent claims, results, datasets, methods, contributions, or limitations. If a required section is absent, state this in working notes and adapt from the closest main-body section without fabricating content.

## Inputs

- Require exactly one selected paper PDF path or attached PDF.
- Ask for the PDF if the user does not provide one.
- Treat focus areas, audience background, and desired page count as preferences only when they do not conflict with this skill.
- Extract journal/conference and year from the PDF or reliable metadata. If unavailable, ask the user or mark it as unknown rather than guessing.
- If the PDF is scanned (no extractable text), render pages and read them visually; note in the working notes that text extraction was unavailable. Never guess unreadable symbols or numbers.

## Non-negotiable numbers

These are machine-checked by `scripts/check_deck.py`; do not approximate them. `assets/style-spec.json` holds the same values in machine-readable form — read it when you need a token instead of opening the reference deck.

| Property | Value |
| --- | --- |
| Slide size | 33.867 × 19.05 cm = 12192000 × 6858000 EMU = 1280 × 720 px at 96 dpi, 16:9 |
| Slide count | ≤ 30 |
| Minimum visible text | 18 pt for all content text — body, table cells, section labels; page numbers are chrome and may be 12–14 pt |
| Section label | 18–30 pt, top 0.4 cm, inset ≥ 0.4 cm, one corner per section |
| Body content inset | ≥ 1.2 cm from left, right and bottom; the top may be 0.8 cm only when the text hangs in the label band and is clear of the label |
| Chrome inset | ≥ 0.4 cm (section label, page number) |
| Latin font | Times New Roman on every run |
| East Asian font | 宋体 (SimSun) on every run |
| Page number | `n / N` bottom-right, 14 pt, grey `#7F7F7F`, skipped on the title slide |
| Speaker notes | every slide, ≥ 60 characters |

## Toolchain

Build the deck as code, never by hand.

- If `@oai/artifact-tool` is available, build from a JavaScript ES module on a 1280 × 720 px canvas.
- Otherwise build with `python-pptx` and set the slide size explicitly to `12192000 × 6858000` EMU.
- Either way, the build must be a re-runnable script so a layout fix is a one-line change, not a redraw.

Run the gates in this order after building:

```bash
python scripts/fix_fonts.py build/deck.pptx          # per-run fonts + language, idempotent
python scripts/add_page_numbers.py build/deck.pptx   # chrome page numbers
python scripts/check_deck.py build/deck.pptx         # mechanical contract check
```

`fix_fonts.py` works on any `.pptx` regardless of the builder. `check_deck.py` exits non-zero on errors. Fix every error before the visual pass; treat warnings as review items.

## Plan before you build

Write `build/plan.json` first and validate it before generating a single slide:

```bash
python scripts/validate_plan.py --init build/plan.json   # starter shape
python scripts/validate_plan.py build/plan.json          # must exit 0
```

The plan lists one entry per slide with `n`, `section`, `layout`, `heading`, `chars`, `assets`, and `notes_chars`. It is cheap to fix here and expensive after building: the validator catches an over-limit slide count, a missing section, a slide planned beyond its character budget, a figure or formula slide with no asset, and a section out of order. A slide holds about 450 characters of readable 18 pt prose; 600 is dense and 800 cannot fit.

## PDF extraction and screenshot cropping

Use `scripts/crop_pdf.py` (poppler backends: `pdfinfo`, `pdftotext`, `pdftoppm`). It replaces eyeballed crops with a measurement:

```bash
python scripts/crop_pdf.py --pdf paper.pdf --page 3 \
    --rect 60,335,300,400 --out figures/eq1.png --manifest figures/eq1.json
```

Rules that the script is built on, and that you must not shortcut:

- `--rect` is given in PDF points with the origin at the top-left and must fully contain the target. The script clips the crop to the detected text column, so the neighbouring column can never bleed in; never crop across a two-column gutter by hand. A full-width table or figure that legitimately spans the gutter must be cropped with `--column full`, otherwise the clamp trims it to one column.
- The script trims the crop to its ink and re-pads it symmetrically (`--pad`, default 6 pt). Keep that behaviour: an equation whose PNG has asymmetric white space looks off-centre even when the picture box is centred, which is the usual cause of "公式错位".
- Read the manifest. `words_inside` lists every text fragment kept in the crop — if it contains body text, a caption, or the next line, the rect was wrong. `warning` reports ink touching the border, which means the crop is truncated.
- Render at a resolution that yields ≥ 300 effective dpi at the placed width. The script's 300 dpi page render satisfies this for images placed at their natural size (`size_cm` in the manifest); if you enlarge an equation beyond `size_cm`, raise `--dpi` proportionally. Never drop below 220 effective dpi; full-width table crops often land at 220–260, which is acceptable.
- For a single-row display equation you may locate it by text instead of a rect: copy the equation's text out of `pdftotext`, then `--text "H = σ(WX + b)" --mode line` (whitespace is ignored when matching). Multi-row equations (matrices, `aligned`, tall fractions with limits) must be given as a rect, because their glyph rows interleave and row matching would cut them.
- When placing a cropped image, set **width only** and let the height follow from the aspect ratio. Setting both width and height is what produces stretched, misaligned equations. `check_deck.py` reports any stretch above 0.5%.
- Place a centred equation at `left = (slide_width - width) / 2`. Never hand-tune an approximate x.

Crop hygiene for figures and tables:

- Crop figures, tables, and display equations so the target is complete, without captions, surrounding paragraphs, or neighbouring objects.
- Do not crop away axis labels, legends, row/column headers, metric names, units, or significant footnotes that belong to the object.
- Keep the equation number `(n)` with the equation when the text refers to it; crop it out otherwise, and be consistent across the deck.
- For a batch of figures and equations, write one job file and run `--jobs jobs.json` once instead of invoking the script per crop.
- For tables, verify legibility as an effective size, not a pixel size. The manifest reports `median_word_height_pt`; the on-slide size is about `median_word_height_pt / 0.9 × (placed_width_cm / size_cm[0])`, and it must stay ≥ 14 pt. A table that fails needs a standalone slide or a split, not a smaller screenshot.
- Inline formulas and symbols inside body text are recreated as text, not screenshots.

## Fonts and math typography

PowerPoint resolves each character of a run against three separate typefaces in `<a:rPr>`. Setting one `fontFace` per run — what most builders expose — cannot satisfy a mixed Chinese/English deck, which is why English silently renders in 宋体.

- Every run carries `<a:latin typeface="Times New Roman"/>`, `<a:ea typeface="宋体"/>`, `<a:cs typeface="Times New Roman"/>`, and `lang="zh-CN"` (plus `altLang="en-US"`) or `lang="en-US"`.
- Do **not** split a mixed-sentence run into Chinese and English runs to get fonts right. One run with the triple renders both scripts correctly; splitting only adds break opportunities and font drift.
- `scripts/fix_fonts.py` guarantees this after the fact for every run, table cell, placeholder, master, layout, and theme font. Run it even when the builder "should" have done it.
- Math typography for recreated formulas: variables and Greek symbols italic (`x`, `λ`, `θ`), function names upright (`max`, `log`, `softmax`), numbers and units upright, vectors and matrices bold upright, operators upright.
- Use `Cambria Math` for symbols that Times New Roman lacks (`∑`, `∇`, `⊙`, `≜`, `‖`); keep `Times New Roman` for ordinary Latin letters and digits.
- On macOS, 宋体 may be absent: substitute `Songti SC` in the same `ea` slot and note the substitution.

## Visual contract

- Minimalist white background, black text; no decorative icons, gradients, ornamental shapes, or visual clutter.
- Every slide shows a section label in a corner: `Title`, `Abstract`, `Introduction`, `Related Works`, `Method`, `Experiments`, `Conclusion`. Keep one corner per section, and keep size and offset identical across the slides of that section; the checker compares labels section by section.
- Every slide after the title carries a page number: `n / N`, bottom-right, 14 pt, grey `#7F7F7F`, right-aligned to the same inset as the body. `scripts/add_page_numbers.py` stamps it and `check_deck.py` requires it.
- Colour is black on white. Grey `#7F7F7F` is reserved for chrome (page number). The accent `#C00000` may be used only in a recreated table, together with bold, to mark the best value of a column; no other colour is allowed.
- Do not use page titles such as `摘要：…`, `介绍：…`, or any colon-form title that repeats the section label and adds a slogan. If a slide needs a heading, use a short subsection heading such as `研究背景`, `模型框架`, `数据处理`, `消融实验`; when the figure or table is the focus, the corner label may be the only title.
- Main language: Chinese. Keep necessary proper nouns, method names, dataset names, model names, symbols, and formulas in English.
- Never reduce text below 18 pt to fit. Split slides instead.
- Use single line spacing. Avoid compressed line spacing, negative paragraph spacing, and auto-fit settings that make adjacent lines collide.
- Visible text boxes must not overlap. If two text regions collide or the reading order is ambiguous, resize, move, split, or simplify.
- Images, tables, and formulas never cover text, section labels, headings, or table values.
- Keep Chinese punctuation off the start of a line: `，。；：、？！）》】` must stay attached to the preceding clause. Adjust wording, box width, or manual breaks to prevent orphans.
- Every slide should feel content-complete. If a slide has little content, centre the main group both horizontally and vertically.

## Text organization

- Prefer paragraph prose over bullet lists, especially in `Method`.
- For paragraph text, use a two-character first-line indent: two full-width spaces `　　` at the start of each paragraph, or an equivalent PowerPoint first-line indent.
- Do not use Markdown-style hyphen bullets (`- …`) in visible slides. If bullets are genuinely useful — contribution lists, experiment settings, table reading guides — use native PowerPoint round bullets and keep them few.
- Abstract, Introduction, and Related Works must not collapse into a few tiny points. Keep enough original detail for a presenter to explain the paper without returning to the PDF. Remove redundancy and low-value citations, but do not over-compress.
- Method slides must track the original method text closely: prefer direct Chinese translation of main-body method paragraphs with only modest redundancy removal.
- Important method definitions, assumptions, computation steps, training details, and subsection transitions must appear on slides, not only in notes.
- Budget the deck before writing: at 18 pt with a 1.2 cm inset, a full-width content slide holds roughly 45 Chinese characters per line and 15 lines, so about 400–550 characters of readable prose. A method section translated faithfully usually needs 5–9 slides. If the budget exceeds 30 slides, cut redundancy in Abstract/Introduction/Related Works first, then merge subsections — never shrink type.

## Required deck structure

Total ≤ 30 slides. Method and Experiments may use as many slides as needed within the limit.

1. **Title**
   - Direct screenshot crop of the PDF title and author area, centred.
   - A text box below with journal/conference and year.
   - Crop away page headers, DOI lines, arXiv side stamps, and logos; if the title block cannot be made legible, use typeset text instead of the screenshot.

2. **Abstract**
   - One slide unless the abstract is unusually long.
   - Faithful Chinese summary covering problem, data/modalities, method, interpretability, evaluation, and key reported results.
   - Paragraph prose preferred; do not reduce it to a few bullets.

3. **Introduction**
   - Two to three slides.
   - Motivation, problem setting, limitations of prior work, and proposed direction in prose.
   - If abstract and introduction are highly repetitive, merge them into `Abstract & Introduction` with three to four slides total.
   - The final introduction slide summarises the paper's core contributions, translating an explicit contributions list directly when present.

4. **Related Works**
   - Two to three slides when the paper has a related-work section.
   - Categories of prior work, representative methods, and the gap the paper positions against.
   - If related work is embedded in the introduction, build the section from those paragraphs and note the source location.

5. **Method**
   - The primary section.
   - If the paper has an overall model, framework, pipeline, or architecture figure, give it a standalone slide before the detailed method slides. Its notes walk through input, output, modules, data flow, training/inference, and each key component's role.
   - Translate main-body method content in detail and put it on slides; do not move the method explanation into notes.
   - Follow the paper's subsection order and start a new slide at each substantial subsection boundary (`3.2` → `3.3`).
   - Omit appendix-only formulas, proofs, derivations, and implementation details unless needed to understand a main-body formula or result.

6. **Experiments**
   - The secondary key section.
   - Start with setup: datasets, tasks, metrics, implementation details, parameters, training settings, and reported baselines.
   - Show all main-body evidence: quantitative tables, qualitative figures, ablations, sensitivity studies, efficiency analyses, user studies.
   - Use screenshot crops for paper tables and figures; large tables may take a standalone slide.
   - Put explanatory detail for dense result screenshots in the notes when slide space should stay legible.

7. **Conclusion**
   - One slide, faithful translation or close summary. Direct translation is preferred when the conclusion is short.

## Speaker notes

Notes are the presenter's script, not a dump for unverified content.

- Every slide gets notes of at least 60 characters.
- Method slides: each component's role, the order of computation, and how the subsection connects to the whole.
- Experiment setup: why these datasets, metrics, and baselines are relevant.
- Result tables: the main comparison, best/second-best patterns visible in the table, and the conclusion it supports.
- Qualitative figures: what to compare and what phenomenon the paper claims.
- Formulas: symbol definitions and what the equation computes or optimises.
- Mark any connective explanation added for presentation clarity as interpretation.

## Fidelity rules

- Preserve the paper's logic and section order unless merging repetitive abstract/introduction material.
- Translate rather than rewrite when a passage is central to method, experiment setting, contributions, or conclusion.
- Do not add external related work, extra benchmarks, or personal critique unless the user asks.
- Avoid overstating results: use `论文报告`, `实验显示`, or `作者认为` when describing claims.
- Keep visible content within the paper's main body unless clearly labelled as presenter-added context in notes.

## Build, gate, and inspect

1. Write `build/plan.json` and run `scripts/validate_plan.py` until it exits 0.
2. Write the build script and generate `build/deck.pptx`.
3. Run `fix_fonts.py`, `add_page_numbers.py`, then `check_deck.py`. Fix every error and re-run until clean.
4. Render every slide to an image and inspect: `soffice --headless --convert-to pdf` followed by `pdftoppm -r 110 -png`, or any equivalent renderer available in the environment.
5. Inspect in this order: screenshot completeness and centring, text overflow and collisions, label consistency, punctuation orphans, legibility of table values.
6. Stop after at most two render-fix cycles for the same slide. If it still fails, change the layout (split the slide, shrink the object count, move prose to notes) instead of nudging coordinates.

Where rendering is unavailable, say so explicitly and deliver with the mechanical gates clean; do not claim a visual inspection that did not happen.

## Final checklist

Run `check_deck.py` and confirm zero errors, then confirm by eye:

- `validate_plan.py` exits 0 for the plan, and the built deck matches it.
- 16:9 at 33.867 × 19.05 cm, ≤ 30 slides.
- Every slide has a section label in its section's corner at 18–30 pt, and the labels agree within each section.
- Every slide after the title has a `n / N` page number in the bottom-right corner.
- Visible outer margins are preserved; only chrome sits closer than 1.2 cm.
- White background, black text, no decorative styling.
- Every run has Times New Roman `latin` and 宋体 `ea`; English is not rendered in 宋体.
- No visible text below 18 pt, including table cells and labels.
- No literal hyphen bullets; paragraph text indented two characters; single line spacing.
- No overlapping text boxes; images and tables never cover text.
- Line breaks leave no punctuation orphaned at a line start.
- Title page shows a clean title/author crop plus a journal/year text box.
- The style asset was used only as a reference; no sample-paper content remains.
- Abstract, Introduction, Related Works, Method, Experiments, and Conclusion are all present and faithful; the method matches main-body wording.
- Every figure, table, and formula is complete, legible, uncropped at its labels, and centred; formulas keep their symbol definitions on the slide or in notes.
- Every slide has speaker notes that could actually be read aloud.
- No invented claims, numbers, datasets, or limitations.
- The rendered preview has no clipped labels, blurry metrics, crowded paragraphs, or stray white bands inside screenshots.

## Reusable style asset

`assets/style-spec.json` is the authoritative token set: canvas, margins, label geometry, fonts, page number, palette, section budget, image rules. Read the numbers there rather than measuring a slide.

`assets/paper-sharing-style-reference.pptx` is a visual sample of that spec, not a template.

- Use it to see how prose-dense method pages, formula pages, table pages, and title pages look at these measurements.
- Do not duplicate it, and replace all sample paper content. No visible content from it may survive unless it also appears in the input PDF.
- Its screenshots come from a low-resolution source, so it deliberately fails the image-resolution warning; a real deck must re-crop with `scripts/crop_pdf.py` at the target dpi.
