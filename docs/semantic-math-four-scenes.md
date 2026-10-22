# Phase 3 — Step 2: semantic roles in four scene contexts

This change does **not** define another math palette. It reuses the
single source of truth in `pipeline/semantic_math.py` created in Step 1.

## Specific scene wiring

- **Worked-example board:** legacy mathematical steps and question headers
  explicitly invoke `TXT(..., math_mode="auto")`. Premium worked examples
  have automatically colored prompts, and every independently verified
  intermediate equation invokes `semantic_text(..., mode="math")`.
- **Practice board:** both legacy questions and solution rows invoke the
  same shared styling; opted-in premium practice uses the exact same math
  mode and expression styling as worked examples.
- **Concept equations:** validated quadratic-function labels use the
  authoritative `MATH()` factory rather than a generic prose `TXT()`
  call; the factory uses the exact same semantic roles as other stages.
  Explanatory concept prose remains neutral unless it contains math.
- **Equation transformations:** the existing vector morph of verified
  intermediate steps now calls `semantic_equation_transform()`, which
  refuses monochrome inputs and any mismatched role-to-color mapping.
  This does not change mathematical state, animation timings or audio
  anchors. Variable, number, operator and relation colors remain
  consistent across each transformation.

## Evidence and acceptance

`tests/test_semantic_scene_integration.py` exercises role certificates,
transitions, invalid color rejection, duration validation and source
integrations without importing Manim in unit CI.

`tests/smoke_render_semantic_contexts.py` uses the **actual embedded
production Manim factories** for worked/practice rows and a concept
equation, plus the actual semantic transform. GitHub Actions renders the
four contexts into one inspectable frame and checks actual image pixels
for six distinct math roles with the existing analyzer. The same CI job
continues to rerender all 25 worked/practice examples and actual narrated
Edge-TTS examples, protecting the previous pipeline behavior.

## Deliberate boundaries

- No lesson-specific letter/number replacement rules.
- No changes to the publishing workflow, daily schedule, YouTube tokens,
  historic uploads or `state/progress.json`.
- Legacy 8-line content limits and formula typesetting trade-offs have
  not been changed. The premium renderer still pages all 25 items.
- This completes **Phase 3 Step 2**, not the Remotion composition phase.
