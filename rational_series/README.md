# Rational Numbers Series — Manim production engine

A data-driven engine that renders **one day of the series per script file**.
Adding Day 4, Day 40 or Day 400 means writing `scripts/dayN.json` and running
one command. No engine file ever changes.

```bash
python render_day.py --day 2          # 1080p60, narrated, captioned, thumbnailed
python render_day.py --day 3
python render_day.py --next           # whichever day hasn't been rendered yet
python render_day.py --list           # what exists, what's pending
```

---

## What the engine derives from the day number

| Derived from `day_number` | Where |
|---|---|
| Background, ink, accents, semantic colours | `color_engine.py` — golden-angle hue walk + seeded hash |
| Thumbnail background / accent / headline colour | `color_engine.py` → `thumbnail.py` |
| Intro motif, backdrop, title entrance, camera path, particles | `intro_generator.py` |
| Chalk wobble seed, recap card colours, motif geometry | seeded from the day everywhere |

Day 1 and Day 2 are 143° apart on the colour wheel; consecutive days are
never closer than 25°, and every foreground colour is contrast-checked
against the surface it sits on (WCAG AAA for text, AA for graphics).

## What the engine derives from the script

| Script field | Effect |
|---|---|
| `concept` (or inferred from the narration keywords) | which animation beat runs |
| `narration` | the spoken line, the caption overlay, and the beat's **time budget** |
| any other key on the block | parameters passed to the beat (`side_label`, `items`, `lines`, …) |
| `keep_stage: true` | the previous beat's visuals stay on screen (square → diagonal → Pythagoras) |
| `hold` | extra seconds of silence after the line |

## Files

```
color_engine.py        procedural palettes + WCAG contrast solver
script_parser.py       JSON/Markdown → blocks, concept detection, timing, SRT
visual_library.py      Style, Chalk, Storyboard, CameraController, HighlightSystem,
                       CaptionTrack, HUD, SquareBuilder, DiagonalAnimator,
                       RecapBuilder, NumberLineBuilder, FractionVisualizer,
                       EquationWriter, ConceptCard, ComparePanels, ClassifyBoard,
                       MistakePanel, ParticleField, GridBackdrop
beats.py               one function per concept — the only place teaching visuals live
intro_generator.py     generate_intro(day) → IntroPlan, and its playback
audio.py               edge-tts narration, caching, ffprobe duration measurement
thumbnail.py           1280x720 card in the day's palette
rational_series_scene.py   RationalNumberDayScene(day_number, script_path)
scripts/               one file per day — the only thing you write
```

## Writing a day script

Minimum viable day:

```json
{
  "day": 4,
  "title": "Recurring Decimals to Fractions",
  "subtitle": "One trick with algebra",
  "topic": "Number Systems",
  "blocks": [
    { "concept": "intro",  "narration": "Welcome back. This is Day 4…" },
    { "concept": "recap",  "narration": "Let's quickly recap Day 3.",
      "items": ["Denominators of 2s and 5s terminate", "Everything else recurs"] },
    { "concept": "equation", "narration": "Call the decimal x…",
      "lines": ["x = 0.\\overline{3}", "10x = 3.\\overline{3}", "9x = 3", "x = \\frac{1}{3}"],
      "box": 3, "box_color": "success" },
    { "concept": "outro",  "narration": "Tomorrow we…", "next_up": "Surds" }
  ]
}
```

Markdown works too (`scripts/day4.md`):

```markdown
# Day 4 — Recurring Decimals to Fractions
- subtitle: One trick with algebra

## recap
- items: Denominators of 2s and 5s terminate | Everything else recurs
Let's quickly recap Day 3.

## draw_square
- side_label: 1 m
Draw a square measuring one metre by one metre.
```

### Concepts available

`intro` · `recap` · `statement` · `definition` · `draw_square` · `draw_diagonal`
· `pythagoras` · `number_line` · `fraction` · `equation` · `contradiction`
· `classify` · `compare` · `mistake` · `practice` · `outro`

Leave `concept` out and the parser infers it from the narration
("Let's quickly recap…" → `recap`, "Draw a square…" → `draw_square`,
"Now draw the diagonal" → `draw_diagonal`). An explicit `concept` always wins.

### Adding a new concept

1. Add a builder to `visual_library.py` (or reuse the existing ones).
2. Add `@beat("your_concept")` in `beats.py`.
3. Add a keyword rule to `CONCEPT_RULES` in `script_parser.py` and list the
   name in `KNOWN_CONCEPTS`.

Every existing day keeps rendering exactly as before.

## Narration sync

`audio.py` renders each block with edge-tts (`en-GB-RyanNeural`), measures the
real duration with ffprobe and caches the mp3 by content hash. Each beat gets
that measured duration as its budget, and `Storyboard` distributes it over the
beat's steps — so the animation lands with the voice instead of guessing.

Without network or `edge-tts` the engine falls back to a speaking-rate model
(2.55 words/second plus punctuation pauses) and renders silently; nothing
fails.

## Output

```
output/rational_series/day02/
  day02_irrational_numbers.mp4     video
  day02_irrational_numbers.srt     captions, timed from the actual render
  day02_thumbnail.png              1280x720
  day02_cues.json                  block timings, palette, intro plan
  audio/                           cached narration
```

## Preview loop

```bash
python render_day.py --day 2 --quality l --blocks 6   # 480p15, first 6 blocks
python -m rational_series.color_engine 1 2 3          # compare palettes
python -m unittest discover tests                     # engine tests
```
