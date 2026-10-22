# Phase 4 — Remotion scaffold (Step 1 only)

This **isolated**, private TypeScript/React Remotion workspace is the
development shell for Math Concepts Made Easy. It is not a new daily publisher,
does not handle credentials, and does not replace Manim mathematical rendering.

## Run locally

Use Node.js 20+ and npm, from the `remotion/` directory:

```bash
npm install
npm run check
npm run bundle
npm run studio
```

`npm run studio` launches the Remotion Studio with a **one-second diagnostic
composition** at 1920×1080, 30 fps. This intentionally does not yet
represent an educational video.

## Scaffold files

- `src/index.ts` — register the Remotion root exactly once.
- `src/Root.tsx` — diagnostic-only composition registry.
- `src/scaffold/ScaffoldDiagnostics.tsx` — minimal build/preview health check.
- `tsconfig.json` — strict TypeScript and JSX configuration.
- `tests/scaffold.test.mjs` — shell, version, isolation, and import invariants.
- `.github/workflows/remotion-scaffold.yml` — independent, no-publish CI.

## Boundaries and release gates

- Manim remains the **only source of mathematical visuals and facts**.
- The existing Python production stages and nightly/daytime publishing
  schedule do not import or execute this folder.
- Existing lesson progress, upload credentials, and YouTube schedules are
  untouched.
- No Manim media bridge, caption overlay, Shorts, YouTube metadata, or rollout
  logic is present at this step.
- No second semantic math palette is introduced. The future Remotion bridge
  must consume the existing Python-verified role styling.

## Fixed implementation sequence (do not skip)

**Completed:** Phase 4 Step 1 — Start Phase 4 Remotion scaffold.

**Next: Phase 4 Step 2 — Build Remotion lesson composition.**

Later, in order: connect Manim outputs into Remotion timeline; add caption
overlays; add Shorts composition; run one complete hybrid demo; only then
consider production rollout.
