# Math Concepts Made Easy — Daily Video Autopilot

This repository turns one curriculum entry into a narrated, animated math
lesson, three vertical Shorts, captions, and a thumbnail, then publishes the
package to YouTube automatically.

## Current production status

- Every lesson listed in `state/progress.json` under `uploaded` is uploaded and
  scheduled for release or already published, and
  locked against duplicate uploads.
- `next_day` is the single lesson eligible for the next production run; it
  advances only after YouTube confirms the upload.
- The scheduled workflow starts at **06:00 America/New_York** every day.
- The main lesson is uploaded privately with YouTube `publishAt` and becomes
  public at **09:00 America/New_York**. The schedule is daylight-saving safe.
- No manual verification is required. Automated tests, semantic lesson QA,
  media validation, and a successful YouTube API upload are required before the
  day counter advances.
- If upload fails, the counter stays on the same lesson and the next scheduled
  run reuses completed per-asset upload receipts. An ambiguous upload stops for
  reconciliation rather than inserting a duplicate video.
- The daily workflow uses the verified **Manim–Remotion hybrid pipeline**.
  All three Shorts have a separate **native 1080 × 1920** layout; their
  portrait teaching boards are authored separately from the full lesson.
  [Native portrait rendering and publishing safeguards](docs/native-shorts-production.md).

The next scheduled run reads its lesson number from `next_day`; no test or
workflow is tied to a fixed video number.

## Commands

```bash
python autopilot.py --hybrid                 # next open lesson
python autopilot.py --hybrid --upload        # render and upload locally
python autopilot.py --hybrid --from-stage 5  # resume at Manim rendering
pytest -q                           # fast regression suite
```

Normal commands reject every uploaded lesson and any out-of-sequence day.
`--allow-locked-day` is an emergency render-only override and should not be
used by automation or for duplicate uploads.

## Content-driven pipeline

1. `pipeline/cell1_lesson.py` validates curriculum content, selects teaching
   stages, rotates hooks/outros, and writes narration.
2. `pipeline/cell2_script.py` creates the JSON visual scene manifest.
3. `pipeline/cell3_audio.py` creates Edge-TTS audio and word timings.
4. `pipeline/cell9_quality.py` fails closed on semantic coverage, pacing,
   narration/action sync, LaTeX, and creative repetition.
5. `pipeline/cell4_animation.py` renders the selected manifest scenes with
   Manim and narration-timed visual reveals.
6. `pipeline/hybrid_assembly.py` assembles the full lesson in Remotion and
   creates SRT/VTT captions from the same frame-quantized timeline.
7. `pipeline/cell6_thumbnail.py` creates the thumbnail.
8. `pipeline/native_shorts.py` creates separate portrait HOOK, FORMULA and
   MISTAKE teaching boards with complete narration and synchronized captions.
9. `pipeline/media_gate.py` validates final media and native-render receipts
   before the uploader may call YouTube.

Legacy FFmpeg assembly and landscape-derived Shorts remain development
commands; the scheduled publisher always passes `--hybrid`.

The planner may select these teaching stages when the lesson content supports
them: hook, intuition, definition, diagram/model, formula/rule, worked example,
common mistake, student pause, and recap. The renderer compatibility step names
are an implementation detail; lesson content is not hard-coded in scene code.

The scene manifest records, for every scene:

- purpose and learning purpose;
- narration and sentence beats;
- stable object IDs;
- registered visual actions and narration timing markers;
- expected and exact audio duration;
- transition style.

`pipeline/visual_actions.py` owns the reusable action registry. It includes
formula writing and transformation, diagrams, triangles, circles, fractions,
number lines, coordinates, graphs, tables, substitution, simplification,
wrong/correct comparison, pauses, reveals, highlights, and camera focus.

## Phase 1: computed mathematical visuals (opt-in)

The repository now supports a **validated quadratic-function scene model**
through `pipeline/math_models.py`. This feature is opt-in: no existing
curriculum lesson changes its animation until it supplies explicit coefficients.

Example lesson field:

```json
"math_model": {
  "kind": "quadratic_function",
  "coefficients": {"a": 1, "b": -3, "c": 2},
  "domain": [-2, 4],
  "samples": 65
}
```

The model computes the parabola, vertex, real zeros, axis of symmetry,
y-intercept and curve samples using exact arithmetic where possible.
Manim plots those computed values in the existing concept scene instead
of a generic formula-only fallback. The scene QA rejects inconsistent
model coordinates. Unsupported mathematical model types are rejected.

### Real Manim render regression

A separate `Phase 1 Mathematical Render Smoke` GitHub workflow tests the
**actual production quadratic helper**, extracts two rendered frames, and
fails on empty/non-mathematical output. It does not publish videos or
change lesson progress. Preview MP4, frames and JSON findings are saved
as a workflow artifact. To reproduce locally after installing Manim,
FFmpeg, and project dependencies:

```bash
python -m pytest -q
python -m manim -ql --disable_caching --media_dir build/phase1-smoke \\
  -o phase1_quadratic_smoke.mp4 tests/smoke_render_phase1.py Phase1QuadraticSmoke
```

This is a component-level validation, **not** proof that every Grade 9–12
topic has a computed visual or that a complete published lesson has passed
premium render inspection. The existing daily YouTube workflow stays the
sole scheduled publisher.

## Automatic posting

`.github/workflows/daily-video.yml` is enabled by its cron schedule. It uses two
UTC cron entries plus a New York timezone gate so the local schedule remains
06:00 through daylight-saving changes. Scheduled runs always use public release
mode and set the main-video release to 09:00 local time.
Shorts release at 12:00, 18:00 and 22:00 local time. Missed slots move to the
next local day. A manual first-day kickoff can schedule the full lesson later
today if the morning slot has passed. YouTube processing may delay availability.

Required GitHub Actions secrets:

- `YT_CLIENT_SECRET_JSON`
- `YT_TOKEN_JSON`

Repository variable `YT_PRIVACY` affects manual runs only; scheduled runs are
always configured for the 09:00 public release.

Keep the Google OAuth consent app in production status; testing-mode refresh
tokens may expire. The recovery-only `Publish Lesson to YouTube` workflow can
retry an artifact after a credential outage without re-rendering it.

## Curriculum and output

Lesson data lives in `curriculum/*.json`; code should never contain a
lesson-specific answer. Outputs default to `output/` and can be redirected with
`MCME_OUTPUT_DIR`.

Important state:

- `state/progress.json` — uploaded lock, next eligible day, and schedule;
- `state/creative_history.json` — recent hook/outro variants used to prevent
  repetition.

Quality reports are written to `output/logs/day_XXX_coverage.json` and included
in the workflow artifact with the video package.

## Repository layout

```text
autopilot.py             orchestration and posted-day lock
curriculum/              data-only lesson catalogue
pipeline/                planning, narration, timing, rendering, QA, assembly
uploader/                YouTube OAuth and upload/scheduling
state/                   progress and creative-rotation history
tests/                   manifest, timing, lock, and schedule regressions
.github/workflows/       CI, daily autopilot, and upload recovery
legacy/                  immutable posted-video policy
```


## Cinematic inverse-functions rebuild

The new full-frame `InverseFunctions` lesson has 60 authored mathematical beats,
equal-scale graph reflection, domain restrictions and optional sidecar captions.
See [preview, narration build and review status](docs/cinematic-inverse-functions.md).
