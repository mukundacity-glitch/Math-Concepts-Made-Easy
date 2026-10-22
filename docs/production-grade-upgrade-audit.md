# Production-grade animation upgrade — audit and safe rollout

Audit date: 2026-10-22. Scope: existing default branch; no change to production
schedules, credentials, progress state, or completed lessons in this PR.

## A. Verified architecture

- `autopilot.py` orchestrates staged curriculum, narration, TTS,
  QA, Manim scenes, assembly, captions, thumbnails and Shorts.
- `pipeline/lesson_plan.py` selects compatibility renderer stages.
- `pipeline/scene_manifest.py` and `visual_actions.py` construct a
  nominally declarative scene contract. `cell2_script.py` copies fields into
  the timed render script.
- `pipeline/cell4_animation.py` is an existing ~94 KB Manim
  renderer with nine stage-specific implementations and audio-time helpers.
  It already has reusable diagrams and illustrations, so it must not be
  discarded for a new framework.
- `lesson_qa.py` checks action IDs, narration sentence coverage and estimates.
  `media_gate.py` requires main media, thumbnail, captions and three Shorts.
- The curriculum currently contains 130 lessons: Grade 9 (21), Grade 10
  (19), Grade 11 (40), Grade 12 (30), university (20). Preserve all tracks.
- `state/progress.json` on the audited default branch shows uploaded 1–42,
  locked through 42 and next_day 43. This is repository state, **not**
  independent confirmation of every YouTube listing.

## B. Confirmed shortcomings and severity

**P0 — publishing idempotency and truthful completion.**
`uploader/youtube_upload.py:upload_day` uploads the main lesson first and
then three Shorts in sequence without a durable asset-level upload ledger.
If a Short/API request fails after the main insert succeeds, the daily
workflow leaves `next_day` unchanged, but a retry can reinsert the main.
Missing shorts are skipped in uploader (the earlier media gate normally
blocks missing files). Successful video insertion also does not imply that
optional thumbnail/caption uploads succeeded. `_compute_local_publish_at`
returns None after a slot has passed, causing public-mode uploads to release
immediately. Hardening needs an explicit recovery policy.

**P0 — content promises vs enforced checks.** Historical and future
`board_examples` fields are lines of working, not independent structured
worked-example or question objects. `validate_lesson` checks only >=1
worked line and >=1 practice item. Existing regression checks require >=2
worked lines, >=1 practice line. The Manim worked-example stage caps display
to 8 lines. The system therefore does **not** presently establish 10
complete worked examples or 15 independent practice questions per lesson.

**P0 — animation semantics.** `visual_actions.build_visual_spec` cycles
through static `STAGE_ACTIONS` roughly every seven seconds against generic
title/model/formula object IDs. `lesson_qa` validates that action names
exist and nominally cover narration sentences, not that the renderer
executes the named mathematical operations. Several actual concept visuals
are selected by keyword heuristics and fallback to formula boxes. This is
not yet evidence of topic-specific, mathematically valid animation.

**P1 — visual QA.** Syntax/audio/ffprobe checks are useful but no current
gate inspects representative rendered frames for label overlap,
misleading visual math or scene quality. Need frame sampling and a manual
promotion step for the first new model.

**P1 — curriculum dependencies.** Curriculum metadata contains a
human-readable `prerequisite`; a machine-checked prerequisite DAG and
per-question verified answers are not implemented.

**P1 — creative repetition.** `creative_history.py` currently retains
hook and outro variants only; visual mechanisms, palette, contexts and
thumbnail approaches are not tracked.

## C. Reference-video teaching principles, applied originally

The reference (3Blue1Brown, `aircAruvnKk`) is valuable for **mechanisms**:
transform a concrete model into symbolic mathematics, maintain visual object
identity, reveal complexity progressively, tie changes to narration, and
highlight changing variables. For this project: maintain a plotted curve while
coefficients change, trace a secant until it becomes tangent, or keep equal
weights on both sides during algebraic operations. Do not reuse reference
footage, music, unique scene layouts, scripts, or branding.

## D. Architecture decision

**Keep Manim as the primary mathematical scene engine.** Use pure Python /
SymPy to calculate validated mathematical states, attach those states to the
existing scene manifest, and let Manim render from those states.

Introduce optional Remotion compositions in a later PR for frame-driven
orchestration, responsive text/captions, sophisticated compositing, and
landscape/vertical versions. The Remotion bridge should consume the same
validated JSON scene contract; it must not duplicate math logic or require
a second publishing workflow. Node/Remotion dependencies should only be
added alongside an executable adapter, tests and rendered proof.

## E. First implementation slice in this PR

- **New `pipeline/math_models.py`:** explicit opt-in
  `math_model: {kind: quadratic_function, coefficients: {a,b,c},
  domain: [min,max], samples: N}`. Computes the curve, real roots,
  discriminant, vertex, axis and intercepts from exact rational
  coefficients. Rejects malformed inputs and validates derived geometry.
- **`pipeline/scene_manifest.py`:** gives opt-in concept scenes their
  computed model, stable computed-curve object and plot action.
- **`pipeline/cell2_script.py`:** forwards the model into the existing
  timed script consumed by Manim.
- **`pipeline/cell4_animation.py`:** an opt-in quadratic graph using
  actual coefficients and Manim `Axes.plot`; curve and valid-coordinate
  markers are drawn within the existing concept panel.
- **`pipeline/lesson_qa.py`:** rejects modified or inconsistent computed
  models before rendering.
- **New `tests/test_math_models.py`:** exact/sampled geometry, zero real
  roots, malformed models, tampered coordinates, manifest connection,
  untouched legacy compatibility.

No existing curriculum entry is opted in in this PR. Current production
rendering remains unchanged until a per-topic fixture and a rendered,
visually inspected lesson prove readiness. A computed model is not itself
a passing visual-inspection report.

## F. Publishing verification

`.github/workflows/daily-video.yml`: UTC cron 10:00 and 11:00 with a
New York offset gate for **06:00 local**; scheduled public upload uses
`YT_MAIN_PUBLISH_LOCAL_TIME=09:00`. The uploader defines 12:00 HOOK,
18:00 FORMULA and 22:00 MISTAKE local slots. This is DST-aware in code,
although GitHub scheduled starts can be delayed.

The inspected 2026-10-22 scheduled workflow run succeeded in GitHub Actions.
That proves an Action concluded successfully, not that all YouTube
assets/times or visual-content standards were independently checked.

## G. Planned order after review

1. **Next PR — structured lesson contracts:** explicit worked examples,
   15 practice questions with answer/solution objects, prerequisite IDs,
   SymPy-backed validation, and automatic fail-closed checks. Avoid silently
   accepting old two-line lesson objects as ten examples.
2. **Math-renderer expansion:** balance equations, transformations,
   trigonometric unit circle, statistics and probability; each with computed
   intermediate states and rendering regression fixtures. Activate one
   actual lesson at a time after visual inspection.
3. **Timing and creative direction:** generate operations from word-level
   cues, maintain object identity and record visual choices/history.
4. **Hybrid composition:** introduce Remotion only after evidence that the
   existing Manim renderer's limitations justify it; test 1080p landscape
   and 9:16 outputs.
5. **Render-level quality gate:** sample frames, detect black/empty frames,
   bounds/clipping, and check timed reveals; human-review first sample.
6. **Idempotent publishing:** persisted per-asset IDs/statuses, thumbnail
   and caption completion, crash recovery, correct handling of missed
   publication windows, and monotonic progress transition after *all*
   mandatory assets are confirmed.
7. **E2E staging demonstration:** quadratic-functions long-form lesson,
   10 verified examples, 15 verified practice questions, three Shorts,
   thumbnail, SRT/VTT, source and frames for human review.
8. **Controlled production promotion:** only merge to `main` after
   regression tests and manually reviewed rendered demonstration; existing
   daily schedule remains the sole production publishing workflow.

## Acceptance status

This first PR adds computed geometry and an opt-in concept renderer.
**Not yet complete:** full lesson-depth contract, motion interpolation,
Remotion bridge, frame inspection, crash-safe uploading and rendered
demonstration. No claim of full production readiness is made.
