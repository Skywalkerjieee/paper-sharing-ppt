# Paper Sharing PPT

`paper-sharing-ppt` is a Codex skill for creating Chinese lab-meeting paper-sharing PowerPoint decks from one selected academic paper PDF.

It is designed for graduate group meetings where a presenter shares a recent high-impact paper related to their research topic. The skill reads the paper PDF as the source of truth and generates a `.pptx` deck with Chinese explanations, paper figure/table screenshots, formulas, and presenter notes.

## What It Produces

- A source-faithful Chinese paper-sharing PPTX deck.
- Minimal academic style: white background, black text, no decorative icons or visual clutter.
- 16:9 landscape slides sized 33.867 cm x 19.05 cm.
- Chinese text in SimSun and English/formulas in Times New Roman where supported.
- Body text at 18 pt or larger.
- Required sections: Title, Abstract, Introduction, Related Works, Method, Experiments, and Conclusion.
- Presenter notes for figures, tables, formulas, and slides that need explanation.
- Figure, table, and display-equation screenshots cropped from the original PDF.

## Key Layout Rules

The skill emphasizes readable, conservative academic layout:

- Every slide has a small section label in the upper-left or upper-right corner.
- Every slide keeps visible margins on all four edges; content must not touch or crowd the canvas boundary.
- Text boxes must not overlap, and images/tables/formulas must not cover text.
- Text boxes use single line spacing.
- Chinese punctuation must not appear alone at the beginning of a line.
- Paragraph prose is preferred over bullets, especially in the Method section.
- Visible Markdown-style `-` bullets are not allowed; if bullets are needed, use native PowerPoint round bullets.
- Method slides should closely follow the original paper text, preferably as direct Chinese translation with only modest redundancy removal.

## Repository Structure

```text
paper-sharing-ppt/
  SKILL.md
  README.md
  agents/
    openai.yaml
  assets/
    paper-sharing-style-reference.pptx
```

`assets/paper-sharing-style-reference.pptx` is a reusable style reference only. It should guide spacing, typography, figure placement, and presenter-note usage, but generated decks must be re-laid out for the selected paper instead of mechanically copying the reference deck.

## Installation

Clone this repository into your Codex skills directory:

```powershell
git clone https://github.com/Skywalkerjieee/paper-sharing-ppt.git "$env:USERPROFILE\.codex\skills\paper-sharing-ppt"
```

After installation, restart or refresh Codex so the skill can be discovered.

## Usage

Provide one academic paper PDF and ask Codex to use the skill, for example:

```text
Use $paper-sharing-ppt to create a Chinese lab-meeting paper-sharing PPTX from this selected paper PDF.
```

The skill expects exactly one selected paper PDF. It should not invent claims, results, methods, datasets, or limitations beyond the PDF.

## Notes

This repository contains the skill instructions and reusable style asset. Generated PPTX decks, rendered slide previews, extracted PDF crops, and temporary build files should stay outside the repository.
