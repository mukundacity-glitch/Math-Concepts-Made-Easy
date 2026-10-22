# Shared semantic math colors — Phase 3 finishing polish

## One stylesheet, not lesson-specific coloring

The sole authoritative palette is `MATH_PALETTE` in
`pipeline/semantic_math.py`. Do **not** add arithmetic-symbol color
replacements inside scene classes or individual curriculum JSON files.

| Mathematical role | Color | Purpose |
|---|---|---|
| Variable | `#38BDF8` cyan | x, y, a, b, θ, etc. |
| Number | `#FDE68A` pale gold | Decimal, integer, coefficients |
| Operator | `#FB923C` orange | +, −, ×, ÷, /, * |
| Relation | `#4ADE80` green | =, ≠, ≤, ≥, ≈ |
| Exponent | `#D8B4FE` violet | ², ³, ^4, ^{12} |
| Grouping | `#CBD5E1` light gray | (), [], {} |
| Function | `#F9A8D4` pink | sin, cos, log, ln, sqrt |
| Neutral text | `#E5E7EB` light gray | Explanation/prose |

Contrast of each color is checked against the dark card background.

## Scope

- **All nine legacy Manim scenes:** `TXT` is now an
  `auto`-classification wrapper that leaves titles and ordinary narration
  neutral but colors embedded equations/expressions. `MATH` explicitly
  requests mathematical styling. Their callers across formula, concept,
  worked-example, mistakes, practice, summary and supporting figures
  inherit the palette automatically.
- **Premium 10+15 question renderer:** prompts use auto classification;
  every checked intermediate mathematical state is styled in math mode,
  preserving exactly the same role color through vector morphs. Final answer
  boxes retain emphasis through their outer green outline.
- **Computed geometry labels:** actual triangle sides and circle
  measurements use the same mathematical typography as algebra boards.
- **Future Remotion:** consume the single palette mapping and verified math
  tokens rather than creating a second notion of mathematical truth or color.

## Engine contract

`tokenize_math` returns `MathSpan(text, role, start, end)`, preserving the
exact mathematical display string. `markup_for_math` creates safe escaped
Pango markup, with no string-specific replacements. `semantic_text` is the
single lazily imported Manim factory; user text is never treated as unescaped
markup. It scales to fit existing board bounds.

Use `mode="math"` for explicitly validated math, `mode="auto"` for mixed
text/equations, or `mode="prose"` for deliberate copy that might resemble
mathematics (e.g. production dates).

Examples under test:

- `x + 2 = 5`
- `2x + 3x = 5x`
- `x² + 4x + 4 = 0`
- `a² + b² = c²`
- `(x + 3)(x - 2) = 0`
- `x + -3 = 5`
- `sin(x) + log(2) = 0`

## Verification

Run `python -m pytest -q` for tokenizer, contract and curriculum tests.
The existing single Manim CI workflow also renders a genuine semantic
math color card and inspects pixel samples for six distinct color roles.
The existing 10-worked/15-practice narrated render CI continues to ensure
new typography does not break live speech alignment.

**Production constraints:** no changes to `state/progress.json`, lesson
history, YouTube upload workflow, or scheduled publication. This is
presentation-layer styling only, not a new editor, composition system
or YouTube task.

**Limitation:** LaTeX formulas are converted to the existing clean Unicode
display representation before Pango rendering. Fractions therefore appear
as `a/b` instead of vertically stacked typeset fractions. High-fidelity
MathTex glyph styling is a possible later enhancement; it is not implied
to be complete by this step.
