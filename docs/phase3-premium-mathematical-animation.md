# Phase 3 — computed, synchronized, 25-item mathematics animation

## Design boundary

- **Single source of mathematical truth:** schema-2, exact-SymPy-verified
  educational content. Every displayed equation state is taken from those
  verified mathematical steps.
- **One existing publisher:** the nine-stage Manim + Cell-3 TTS/audio
  workflow remains unchanged for legacy daily lessons. No alternate upload
  flow, scheduler, progress state or historical-curriculum migration.
- **Opt-in only:** a future lesson must explicitly include
  `educational_content` and a verified `concept_id` for premium
  rendering. Incomplete content fails before video production.
- **Remotion scope:** reserved for subsequent compositing phase. Mathematical
  invariants must remain independent of Remotion/React.

## Implemented execution

1. Load the 10 worked and 15 practice items from the verified schema.
2. Generate an individual spoken introduction, question, at least two
   explained mathematical states, and a verified-answer cue for each item.
3. Include EVERY item in Cell-1 TTS narration, so Cell 3 creates actual
   speech/word timestamps, rather than trying to fit 25 answers into a
   narration that never speaks them.
4. Carry every item/step/cue in the manifest and the timed Cell-2 script.
   Each item has a stable object ID and declared display/transform/box
   actions.
5. Require the exact cue sequence in the *spoken narration* and the
   exact independently validated item math in the *visual payload*.
6. The Manim worked-example scene shows all 10 items; the practice
   scene shows all 15 items. Both render one readable card at a time,
   clearing before the next problem; the old 8-line truncation applies
   to legacy board-only lessons **only**.
7. Morph the actual equation state from each checked mathematical step
   to the next using vector `TransformMatchingShapes`, preserve
   on-screen continuity, and separately highlight the validated answer.
8. For premium scenes, require the actual Cell-3 MP3 and its word boundary
   list; missing cues/timing are fatal (never silently estimate).
9. Support independently calculated quadratic functions, 2D right
   triangles and circles, including computed vertices, side lengths,
   hypotenuses, areas and radii. The concept diagram is selected by
   declared mathematical model kind, not title heuristics.
10. Enforce structural and exact-math regression tests, plus real-Manim
    render-frame smoke checks.

## Narrated video acceptance

Two complementary test modes are included in the existing GitHub Actions
Manim regression suite:

1. **Deterministic visual smoke:** synthetic word timestamps with silent
   placeholder MP3s verify readable Manim animation of **all 10 worked
   examples and 15 practice solutions**, including every vector morph.
2. **Actual narrated 25-question smoke:** an independent test calls
   Edge-TTS using the same Ryan voice family as production, saves real
   emitted WordBoundary timestamps, verifies every worked/practice
   question/step/answer cue, then renders full Manim worked and practice
   clips against the generated speech. MP4s must contain an audio stream.
   The pipeline FAILS when speech generation or cue verification fails.

This is a real *component-level* narrated sample, not a fully composed
nine-stage published lesson with YouTube metadata. The default legacy
Cell-3/Cell-4 production workflow remains the sole publisher.

A separate strict audio gate in `pipeline/premium_audio_qa.py` runs in
both Cell-3 TTS processing and the Manim renderer, rejecting missing
timestamps and unreadable/out-of-order cues for opted-in premium lessons.
This catches the otherwise dangerous silent fallback from Edge-TTS to
un-timed gTTS before rendering or publication.

## Acceptance tests and constraints

- At least 10 distinct worked and 15 distinct answered practice items.
- Unique stable visual object ID per item; all steps and answers must match
  their independently verified exact schema.
- Each question/step/answer has one chronological spoken cue, and a
  corresponding registered visual action.
- Word timing must come from generated speech boundaries, not
  character-count interpolation, in a live premium render.
- Any unsupported math kind or tampered coordinates fail closed.
- Real clip evidence (frames, durations, MP4s) must pass explicit
  render-level checks before merging.
- No modifications to `state/progress.json`, the daily upload workflow or
  already completed lesson data.

## Next stages, not claimed by this phase

Broaden verified domain-specific math solvers across every Grade 9–12
chapter, replace generic art in remaining nonpremium visual stages,
and add Remotion hybrid layouts, caption tracks, custom thumbnails and
frame-by-frame compositing. The complete main-lesson and 3-Short
publication guarantees require an idempotent asset upload ledger and
schedule fix in a separate production-release phase.
