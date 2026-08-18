# Plan: Redo 19 → Redo 20 → Auto from 21

## State on GitHub
- `next_day`: **19**
- `completed` / `uploaded`: **1–18 only**
- `MIN_OPEN_DAY`: **19** (days 1–18 blocked)
- Engine: **ENGINE_VISUAL_V2**

## Your steps

### A) Day 19 (manual now)
1. Delete/unpublish old Day 19 on YouTube (you said you already deleted it).
2. GitHub → **Actions** → **Daily Lesson Video** → **Run workflow**
3. Day number: **`19`**
4. Privacy: `private` first to review, or `public` if ready
5. In logs confirm: `ENGINE_VISUAL_V2`
6. Check video: unit-triangle / opp-adj-hyp style visuals + sin/cos/tan board

### B) Day 20 (manual after 19 looks OK)
1. Delete/unpublish old Day 20 on YouTube if still there.
2. Run workflow day **`20`**
3. Confirm identity triangle + sin²+cos² derivation visuals
4. Publish when happy

### C) Auto from tomorrow = Day 21
After a **successful** Day 20 autopilot run, progress advances:
- `next_day` → **21**

Then the **scheduled** daily job (19:00 UTC) will pick Day 21 automatically.
You do **not** need to run Day 21 manually unless you want it earlier.

## If you run only 19 and stop
`next_day` becomes **20**. Schedule would do Day 20 next — not 21.  
To land on 21 for tomorrow you must **finish Day 20** (or set `next_day` to 21 by hand after accepting old/new 20).

## Order matters
**19 first → 20 second → leave the rest to schedule (21+).**
