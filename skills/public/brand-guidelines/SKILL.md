---
name: brand-guidelines
description: Applies Anthropic's official brand identity — palette (dark #141413, light #faf9f5, orange/blue/green accents) and typography (Poppins headings, Lora body) — to slides, docs, PDFs, and HTML artifacts. Use ONLY when the user explicitly asks for Anthropic branding, Anthropic style, or the Anthropic look-and-feel by name, or is restyling an existing artifact to match it. Do NOT trigger for generic requests like 'make it look professional', 'style this', 'add branding', or any other company's brand — for general theming use theme-factory; for the user's own brand, ask for their brand assets instead.
license: Complete terms in LICENSE.txt
---

# Anthropic Brand Styling

Apply the palette and type rules below directly — there is no script in this skill; you do the styling yourself in whatever medium the artifact uses (python-pptx, docx, CSS, SVG, matplotlib, …).

## Palette

| Role | Hex | Use for | Never use for |
|---|---|---|---|
| Dark | `#141413` | Body text on light, dark backgrounds | — |
| Light | `#faf9f5` | Page/slide backgrounds, text on dark | Text on light backgrounds |
| Mid gray | `#b0aea5` | Secondary text, captions, dividers | Body text (fails contrast) |
| Light gray | `#e8e6dc` | Subtle fills, table stripes, cards | Text |
| Orange | `#d97757` | Primary accent: highlights, links, first data series | Body text, large fills behind text |
| Blue | `#6a9bcc` | Secondary accent, second data series | Body text |
| Green | `#788c5d` | Tertiary accent, third data series | Body text |

Rules that resolve the common ambiguities:

- **Backgrounds come in exactly two modes**: light mode = `#faf9f5` background with `#141413` text; dark mode = `#141413` background with `#faf9f5` text. Pick one per artifact (light is the default) — do not mix modes across slides/sections of the same artifact.
- **Accents cycle in fixed order** orange → blue → green (shapes, chart series, callouts). If a fourth category is needed, reuse the cycle at reduced opacity (60%) rather than inventing new hues.
- **Contrast**: mid gray is decorative/secondary only. Any text under 18px/14pt must be Dark on Light (or Light on Dark) — never an accent color, never mid gray.
- **Charts/data viz**: series colors in accent order; gridlines `#e8e6dc`; axis text `#141413`. Do not use red/green semantics — if you must signal good/bad, use green `#788c5d` vs orange `#d97757` and label explicitly.

## Typography

- **Headings**: Poppins. Fallback: Arial. In HTML/CSS use the stack `Poppins, Arial, sans-serif` — do not fetch fonts from the network; if Poppins isn't installed the fallback is the intended behavior, not a failure to fix.
- **Body**: Lora. Fallback: Georgia. CSS stack: `Lora, Georgia, serif`.
- The heading/body split is by role, not size: titles, section headers, and slide headlines get Poppins; paragraphs, bullets, captions, and table cells get Lora. (In pptx, a practical proxy: runs ≥ 24pt are headings.)
- Code blocks and terminal output keep a monospace font and are exempt from brand fonts and accent colors.

## Edge cases

- **Restyling an existing artifact**: change only colors and fonts; never rewrite, reflow, or delete content while applying the brand.
- **Conflict with user's own brand**: if the artifact already carries the user's brand (their logo, their palette), stop and ask which brand wins — do not silently overwrite it with Anthropic's.
- **Mixed-script text**: Poppins/Lora cover Latin. For non-Latin scripts keep a high-quality system font for that script and apply the palette only.
- **Logos**: this skill contains no logo assets. Never draw, trace, or approximate the Anthropic logomark — use text styled per the rules above.
- **Print/PDF**: same palette; ensure the light background is actually rendered (some PDF pipelines drop page background fills — set it explicitly).
