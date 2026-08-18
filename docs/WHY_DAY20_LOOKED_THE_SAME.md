# Why Day 20 looked the same after the first update

## What you observed
Manual Day 20 still felt like the old style: same cards, same rhythm, same generic visuals.

## Root cause
1. Production uses a **fixed Manim 9-scene shell** for every day.
2. Early GitHub updates mostly changed **curriculum JSON + gates + locks**, not the Manim drawer.
3. `cell4_animation.py` had **zero uses of `visual_hints`**.
4. Hook/concept art came from generic `story_visual()` (pizza/money/car…). Trig identity rarely matched → fallback cards.
5. Narration template only spoke a thin slice of `board_examples`.

**Data changed a little; the animation engine did not — until ENGINE_VISUAL_V2.**

## ENGINE_VISUAL_V2
- Topic diagrams: unit-hypotenuse triangle + identity derivation; mean/median outlier strip + sort demo
- `story_visual()` calls `topic_visual()` first
- Concept scene prefers topic diagram
- Narration speaks more worked/practice lines

## Re-run required
Old renders are cached artifacts. You must rebuild from stage 1:

```bash
python autopilot.py --day 20 --no-advance
```

Or Actions → Daily Lesson Video → Run workflow → day `20`.

Upload-only will not change the picture.
