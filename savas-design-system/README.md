# Savas Design System

Source of truth for tokens is `tokens.json` (W3C Design Tokens format). Everything else is generated from it or mapped to it.

| File | What it is |
|---|---|
| `tokens.json` | Colors, type styles, radius, spacing, shadow |
| `tokens.css` | `--sv-*` CSS custom properties (generated) |
| `Savas-Brand-Standards.html/.pdf` | Brand standards page, paged PDF and long PDF (generated, like the WHHA set) |
| `build.py` | `python3 build.py [--pdf]` regenerates all of the above |

Figma file: https://www.figma.com/design/miniCJNlVc3Pw4w9o4mw1F (Savas Labs team)

- **Variables:** Primitives (18 colors), Semantic (18 aliases), Radius (5), Spacing (8). Each variable's WEB code syntax is the matching `--sv-*` property in `tokens.css`.
- **Styles:** `Savas/*` text styles (10) and `Savas/shadow-1|2` effect styles.
- **Pages:** Foundations (specimen), Components (Button, Code chip, Step marker, Section card).

## Loop

1. Designers edit Variables, styles and components in Figma.
2. Ask Claude "sync Savas tokens from Figma": it reads the Variables through the Figma MCP, diffs against `tokens.json`, and updates the file. Open a PR.
3. `python3 build.py --pdf` regenerates `tokens.css` and the brand standards.
4. Sites import `tokens.css`. Review on a preview deploy, then merge.

Tokens and components sync both ways. Page layouts go Figma to code only.

## Known gaps

- SF Mono is not in Figma's font list; the Code text style uses Roboto Mono there.
- Light mode only. Add a Dark mode to the Semantic collection if one is needed.
- Code Connect is not set up yet. It needs the Savas site components in a repo to map to.
