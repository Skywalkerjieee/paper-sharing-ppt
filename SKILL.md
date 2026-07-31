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

## Reusable Style Asset

- Use `assets/paper-sharing-style-reference.pptx` as a local style reference when available.
- Treat the asset as a reference for minimalist academic spacing, section labels, title-page screenshot placement, method formula pages, figure/table pages, and experiment-result pages.
- Do not mechanically duplicate the asset as a fixed template. Recompose each deck around the selected paper's actual title block, section structure, figures, tables, equations, and experimental evidence.
- Borrow only the style language that improves clarity: white background, black text, compact academic layout, small corner section labels, large readable paper screenshots, centered sparse objects, and presenter-note usage.
- Replace all sample paper content from the asset. No visible content from the reference deck may remain in the final deck unless it is also present in the selected input PDF.

## Tool Workflow

1. Read the PDF with text extraction and page rendering tools. Prefer structured extraction for section text and high-resolution page renders for screenshots.
2. Identify main-body sections and page ranges. Exclude appendix, supplementary material, references, author checklists, acknowledgements, funding, and data-availability statements unless the user explicitly requests them or they are part of the paper's main conclusion.
3. Extract title/author block, figures, tables, and display equations by cropping PDF renders. Keep a source map from each slide to original section/page.
4. Review `assets/paper-sharing-style-reference.pptx` for style cues only, then choose layouts based on the selected paper's content needs.
5. Build the PPTX with `@oai/artifact-tool` from a JavaScript ES module. Set the canvas to 1280 x 720 px, corresponding to 33.867 cm x 19.05 cm at 16:9.
6. Add presenter notes to every slide that needs explanation, and always add notes for slides containing figures, tables, or formulas.
7. Render every generated slide to images and inspect visually. Iterate until text, screenshots, tables, formulas, spacing, and notes satisfy the final checklist.

## Visual Contract

- Slide size: landscape 16:9, width 33.867 cm, height 19.05 cm.
- Style: minimalist white background, black text, no decorative icons, gradients, ornamental shapes, or visual clutter.
- Keep a visible safe margin on all four edges of every slide. No text box, figure, table, formula, screenshot, or section label may touch or visually crowd the top, bottom, left, or right edge. For a 1280 x 720 px canvas, use at least about 40 px of outer margin whenever possible; if a large table or figure requires more space, preserve a smaller but still visible margin and never let the object fill the slide edge-to-edge.
- Every slide must show a small section label in the upper-left or upper-right corner, such as `Abstract`, `Introduction`, `Related Works`, `Method`, `Experiments`, or `Conclusion`.
- Do not use page titles such as `摘要：...`, `介绍：...`, or any colon-form title that repeats the section label and adds a slogan. If a slide needs a heading, use a short subsection heading such as `研究背景`, `模型框架`, `数据处理`, `消融实验`; if the figure/table itself is the slide focus, the corner section label may be the only title.
- Main language: Chinese. Keep necessary proper nouns, method names, dataset names, model names, symbols, and formulas in English.
- Chinese font: SimSun/宋体. English font and formulas: Times New Roman.
- Body text, table text, recreated figure annotations, and visible formula definitions must be at least 18 pt.
- Titles and subsection headings may be larger or bold, typically 22-30 pt.
- Never reduce text below 18 pt to force content onto a slide. Split slides instead.
- Apply fonts and sizes explicitly to every visible text object and table cell. For mixed Chinese/English text, split runs by script when possible so Chinese uses SimSun and Latin/formula text uses Times New Roman.
- Use single line spacing for text boxes. Avoid compressed line spacing, negative paragraph spacing, and auto-fit settings that make adjacent lines collide.
- Do not allow visible text boxes to overlap each other. If two text regions collide or make reading order ambiguous, resize, move, split, or simplify content.
- Do not place images, tables, or formulas on top of text. Images must never遮挡文字, section labels, headings, formulas, or table values.
- Handle Chinese punctuation carefully. Do not leave punctuation such as `，。；：、？！）》】` at the beginning of a line, and do not separate punctuation from the sentence it belongs to. Adjust text box width, manual line breaks, or wording to keep punctuation attached.
- Keep screenshots large enough to be legible. Preserve aspect ratio and crop only irrelevant whitespace.
- Every slide should feel content-complete. Avoid excessive empty space; if a slide naturally has little content, center the main text/image/formula group both horizontally and visually vertically.

## Text Organization

- Prefer paragraph prose over bullet lists, especially in `Method`.
- For paragraph text, use first-line indentation of two Chinese characters. In generated PPT text, represent this with two full-width spaces `　　` at the start of each paragraph or an equivalent PowerPoint first-line indent.
- Do not use Markdown-style hyphen bullets such as `- ...` in visible slides.
- If bullets are truly helpful, use native PowerPoint round bullets and keep them limited. Bullets are acceptable mainly for concise contribution lists, experiment setting inventories, or table reading guides.
- Abstract, Introduction, and Related Works must not be reduced to a few tiny points. Preserve enough original detail for a presenter to explain the paper without constantly returning to the PDF. Remove redundancy and low-value citations, but do not over-compress.
- Method slides must align closely with the original method text. Prefer direct Chinese translation of main-body method paragraphs, with only modest redundancy removal and page-fitting edits.
- Important method definitions, assumptions, computation steps, training details, and subsection transitions must appear visibly on slides, not only in presenter notes.
- If visible text is too dense, split it across more slides before shrinking font or converting prose into terse bullets.

## Required Deck Structure

Keep the total deck at or below 30 slides. Method and experiment sections may take as many slides as needed within the limit; reduce repetition in abstract, introduction, and related work first if space is tight.

1. **Title**
   - Use a direct screenshot crop of the PDF title and author area.
   - Center the screenshot clearly on the slide.
   - Add a text box below it with the paper's journal/conference and year.

2. **Abstract**
   - Use one slide unless the abstract is unusually long.
   - Present a faithful Chinese summary with enough detail to cover problem, data/modalities, method, interpretability, evaluation, and key reported results.
   - Paragraph prose is preferred. Do not simply list a few brief bullets.

3. **Introduction**
   - Use two to three slides.
   - Summarize motivation, problem setting, limitations of prior work, and proposed direction in paragraph prose.
   - If the abstract and introduction are highly repetitive, merge them into an `Abstract & Introduction` section with three to four total slides.
   - The final introduction slide must summarize the paper's core contributions. If the paper has an explicit contributions paragraph or list, translate it directly and preserve its meaning.

4. **Related Works**
   - Use two to three slides when the paper has a related work section.
   - Summarize categories of prior work, representative methods, and the gap the paper positions itself against.
   - If related work is embedded in the introduction, create the section from the relevant main-body paragraphs and note the source location.
   - Related-work slides may use sparse native bullets for method categories, but paragraph prose is still preferred when space allows.

5. **Method**
   - Treat this as the primary section.
   - If the paper has an overall model, framework, pipeline, or architecture figure, put that figure on a standalone slide before detailed method slides.
   - In the presenter notes for the architecture slide, provide a walkthrough of input, output, modules, data flow, training/inference process, and the role of each key component.
   - Translate the main-body method content in detail and place the translated methodology directly on slides. Do not move the method explanation only into notes.
   - Follow the paper's subsection order. Start a new slide when moving from one substantial subsection to the next, for example from `3.2` to `3.3`.
   - Use paragraph prose for method descriptions. Avoid bullet lists unless describing a short ordered set of variables or settings.
   - Omit appendix-only formulas, proofs, derivations, and implementation details unless required to understand a main-body formula or result.

6. **Experiments**
   - Treat this as the secondary key section.
   - Start with experiment setup: datasets, tasks, metrics, implementation details, model parameters, training settings, and baselines that the paper reports.
   - Briefly introduce comparison methods when the paper does so.
   - Show all main-body experimental evidence clearly: quantitative comparison tables, qualitative result figures, ablation tables, sensitivity studies, efficiency analyses, user studies, or other reported experiments.
   - Use screenshots for paper tables and figures. Large tables may occupy a standalone slide.
   - Put explanatory text for dense result screenshots in presenter notes when visible slide space should be reserved for legibility.

7. **Conclusion**
   - Use one slide.
   - Translate or summarize the conclusion faithfully. If the conclusion is short, direct translation is preferred.

## Figures, Tables, and Formulas

- Use screenshot crops for all paper figures and tables.
- Crop figures, tables, and display equations so the target object is complete and clear, without captions, surrounding paragraphs, neighboring figures, or page clutter.
- Do not crop away axis labels, legends, row/column headers, metric names, units, or significant footnotes that are part of the figure/table itself.
- For experimental result screenshots, make metric names and values readable; if not possible, use a standalone slide or split the table.
- Inline formulas and symbols inside body text should be recreated as text, not screenshots.
- Centered display equations may be shown as screenshots when that preserves accuracy, but the crop must include only the equation.
- Every formula must be followed by symbol definitions. Put definitions on the slide when space allows; otherwise put them in presenter notes.
- If the paper omits a symbol definition but context makes it clear, add `符号定义（根据上下文）` in presenter notes and keep the inference conservative.
- For every figure, table, or formula slide, presenter notes must include a script that describes the figure, summarizes the table, or explains the formula's symbols and purpose.

## Speaker Notes

Use speaker notes as the presenter's script, not as a dumping ground for unverified content.

- Add notes for any slide where a presenter would need guidance beyond visible text.
- For method slides, explain the role of each component, the order of computation, and how the subsection connects to the overall method.
- For experiment setup slides, state why the datasets, metrics, and baselines are relevant.
- For result tables, state the main comparison, best/second-best patterns if visible, and the conclusion supported by the table.
- For qualitative figures, state what the viewer should compare and what phenomenon the paper claims.
- For formulas, define symbols and explain what the equation computes or optimizes.
- Keep notes faithful to the paper. Mark any connective explanation added for presentation clarity as interpretation.

## Fidelity Rules

- Preserve the paper's logic and section order unless combining repetitive abstract/introduction material.
- Translate rather than rewrite when a passage is central to method, experiment setting, contribution list, or conclusion.
- Do not add external related work, extra benchmarks, or personal critique unless the user explicitly asks.
- Avoid overstating results. Use wording such as `论文报告`, `实验显示`, or `作者认为` when describing claims.
- Keep all visible content within the paper's main body unless clearly labeled as presenter-added context in notes.

## Final Checklist

Before delivering the PPTX, verify all items:

- The deck is a `.pptx` file and has no more than 30 slides.
- Slide size is 33.867 cm by 19.05 cm, landscape 16:9.
- Every slide preserves visible outer margins on the top, bottom, left, and right; no slide content touches or crowds the canvas edge.
- Every slide has a section label at the upper-left or upper-right.
- The deck uses white background, black text, and no decorative icon styling.
- Chinese text uses SimSun/宋体; English and formulas use Times New Roman where the PPT tool permits.
- No visible text, including tables, is smaller than 18 pt.
- Text boxes use single line spacing, and no visible-text boxes overlap or create text-on-text collisions.
- No visible text uses Markdown-style hyphen bullets. Any necessary bullets are native PowerPoint round bullets.
- Paragraph-style text uses two-character first-line indentation or an equivalent PowerPoint first-line indent.
- Abstract, introduction, related works, and especially method are not over-compressed into a few terse points.
- Line breaks are clean: punctuation is not stranded at the beginning of a line, and punctuation remains visually attached to its sentence.
- Title page uses a PDF screenshot of title/authors and a text box for journal/conference plus year.
- The reusable style asset was used only as a style reference; the final deck was re-laid out for the selected paper and contains no leftover sample-paper content.
- Abstract, introduction, related works, method, experiments, and conclusion are represented according to this skill.
- Method slides cover the paper's main-body method content in close correspondence with the original wording, preferably as direct Chinese translation.
- Method and experiment slides cover the paper's main-body content clearly without appendix-only material.
- Figure, table, and display-equation screenshots are complete, legible, and free of captions or surrounding text unless that text is part of the object.
- Images, tables, and formulas do not遮挡文字 or overlap headings/section labels.
- Every figure, table, and formula has presenter notes explaining it.
- Formula symbols are defined on slide or in notes.
- Content is faithful to the paper and does not invent claims or results.
- The rendered slide preview has no overlapping text, cropped labels, blurry result metrics, excessive empty space, or crowded unreadable paragraphs.
