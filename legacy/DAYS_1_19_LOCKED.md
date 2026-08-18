# Posted-day lock policy

## Locked permanently (do not mass re-render)
**Days 1–18** are posted and locked by default (`MIN_OPEN_DAY = 19`).

## Manual redo window (your choice)
| Day | Topic | How to run |
|-----|--------|------------|
| **19** | Trigonometric Ratios (sin, cos, tan) | Actions → day `19` **or** `python autopilot.py --day 19` |
| **20** | Pythagorean Trig Identity | After 19: Actions → day `20` **or** `python autopilot.py --day 20` |

## Automatic schedule (tomorrow onward)
After Day 20 completes successfully, `next_day` becomes **21**.

Daily GitHub Action (`.github/workflows/daily-video.yml` @ **19:00 UTC**) will then produce/upload:
- **Day 21** — Mean, Median, Mode  
- then 22, 23, … automatically

## Do not
- Rewind `completed` below 18 for bulk re-runs of early days
- Re-upload replacements for days 1–18 unless you explicitly override with care
