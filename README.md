# Math Concepts Made Easy — Daily Video Autopilot

This repository turns one curriculum entry into a narrated, animated math
lesson, three vertical Shorts, captions, and a thumbnail, then publishes the
package to YouTube automatically.

## Current production status

- Every lesson listed in `state/progress.json` under `uploaded` is posted and
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
  run retries it.

The next scheduled run reads its lesson number from `next_day`; no test or
workflow is tied to a fixed video number.

## Commands

```bash
python autopilot.py                 # next open lesson
python autopilot.py --upload        # render and upload locally
python autopilot.py --from-stage 5  # resume at Manim rendering
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
6. `pipeline/cell5_assembly.py` assembles the long video.
7. `pipeline/cell8_subtitles.py` creates SRT and VTT captions.
8. `pipeline/cell6_thumbnail.py` creates the thumbnail.
9. `pipeline/cell7_shorts.py` creates HOOK, FORMULA, and MISTAKE Shorts.
10. `pipeline/media_gate.py` validates final media before the uploader may call
    YouTube.

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

## Automatic posting

`.github/workflows/daily-video.yml` is enabled by its cron schedule. It uses two
UTC cron entries plus a New York timezone gate so the local schedule remains
06:00 through daylight-saving changes. Scheduled runs always use public release
mode and set the main-video release to 09:00 local time.

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
