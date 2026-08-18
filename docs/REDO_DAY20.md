# Redo Day 20 with new engine

## Why
First Day 20 render used the old Manim shell. ENGINE_VISUAL_V2 adds topic-specific diagrams and richer narration.

## State
`state/progress.json` is set to:
- `next_day`: 20
- `completed` / `uploaded`: 1–19 only (20 removed from completed)

## Run (pick one)

### GitHub Actions (recommended)
1. Actions → **Daily Lesson Video** → **Run workflow**
2. Day: `20`
3. Privacy: `public` or `private` for review first

### Local
```bash
python autopilot.py --day 20 --upload
```

## Success checks
- Log contains: `ENGINE_VISUAL_V2`
- Hook/concept show **unit triangle** / identity derivation (not empty generic cards only)
- Worked example board speaks multiple lines
- After success, `next_day` becomes 21

## YouTube
Delete or unpublish the old Day 20 upload manually on YouTube, then let this run post the new one.
