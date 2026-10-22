# Phase 4 — Step 2: Premium Remotion Lesson Composition

**Status: the 1920×1080 lesson composition layout is implemented.**
This remains an isolated, opt-in studio/preview workspace. Neither the
existing Manim engine nor the daily publishing pipeline is modified.

## Commands

Install Node.js 20+ and npm. In `remotion/` run:

```bash
npm install
npm run check
npm run bundle
npm run studio
```

Remotion Studio exposes two compositions:

- `ScaffoldDiagnostics` — the original 1-second smoke composition.
- `PremiumLesson` — a data-driven, 1920×1080 / 30fps layout with a title card,
  chapter framing, learning-goal sidebar, progress band, and closing card.

### Data-driven layout

`src/lesson/types.ts` defines validated content props. The total composition
length is **derived from intro, all chapters and outro frame counts**, not
hardcoded around one lesson. `src/lesson/timeline.ts` validates unique chapter
identities, sequence order and frame lengths, so rendered chapters cannot
overlap or disappear. `src/lesson/demoLesson.ts` contains **UI placeholder
content only** for Remotion Studio. It contains no fabricated mathematics.

All layout color/typography is defined in `src/design/theme.ts`. These
are interface-shell colors, **not** a competing mathematical palette. Manim's
verified `pipeline/semantic_math.py` retains complete responsibility for
mathematical content and operator/variable/exponent coloring.

### Design components

- `src/compositions/PremiumLesson.tsx` — intro/chapters/outro sequencing.
- `src/components/TitleCard.tsx` — premium lesson opening.
- `src/components/BrandHeader.tsx` — consistent series and chapter labels.
- `src/components/SceneFrame.tsx` — bounded educational canvas with learning
  objective, safe area and chapter progress. The central panel is clearly
  marked as **unconnected to Manim**.
- `src/components/OutroCard.tsx` — closing layout without invented answers.
- `src/lesson/demoLesson.ts` — editable studio-only props.

The independent Remotion CI workflow runs TypeScript, pure timeline
tests, a Webpack bundle and three full-resolution PNG previews for the
title, chapter, and outro. It rejects blank or identical images.

### Scope boundary

**Not yet present:** Manim video files, an asset/timestamp bridge, audio
synchronization, caption overlays, vertical Shorts, hybrid demo or rollout.
No changes were made to Python's rendering/uploader, schedules,
historical lesson files or `state/progress.json`.

## Approved sequence — follow one step per request

- ✅ Phase 4 Step 1 — Start Phase 4 Remotion scaffold.
- ✅ Phase 4 Step 2 — Build Remotion lesson composition.
- **Next: Phase 4 Step 3 — Connect Manim outputs into Remotion timeline.**
- Phase 4 Step 4 — Add caption overlays.
- Phase 4 Step 5 — Add Shorts composition.
- Phase 4 Step 6 — Run one full demo lesson through the hybrid pipeline.
- Only then consider production rollout.
