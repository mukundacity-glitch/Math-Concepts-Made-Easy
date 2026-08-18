# Days 1–19 are LOCKED (already posted)

These lessons are already produced and uploaded.

Automation **must not**:
- re-render Days 1–19
- re-upload Days 1–19
- rewind `state/progress.json` below day 20
- delete completed/uploaded markers for days 1–19

## Production continues from Day 20

| Field | Value |
|-------|--------|
| `state/progress.json` → `next_day` | **20** |
| First open lesson | Day 20 — Pythagorean Trigonometric Identity |
| Then | Day 21 — Mean, Median, Mode → … through curriculum |

The old single-file Colab export (`math_concepts_colab.py`) was removed.
All production runs go through `autopilot.py` + `pipeline/*` + `curriculum/*.json`.
