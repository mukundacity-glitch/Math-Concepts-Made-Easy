# Inverse functions: full-frame rebuild

The landscape compositor previously placed a 16:9 mathematical animation inside
an inset panel beside a learning-focus sidebar, underneath a header and above a
caption lane. The nested layout reduced the teaching image to a small part of
the 1920×1080 output. `SceneFrame` now gives the original media the complete
canvas and plays its separate voice track exactly once. Sidecar captions remain
available; captions are not burned onto the teaching image.

The new `InverseFunctions` composition is a separately authored replacement for
the Day 43 lesson. It uses original vector mathematics, rather than enlarging
old narration slides. Its nine chapters contain 60 timed teaching beats:

1. A mathematical curiosity hook, channel welcome, title and objective.
2. A token travelling through `3 → ×2 → 6 → +5 → 11`, then returning.
3. Swapping variables, balancing an equation, and deriving `(x−5)/2`.
4. Both orders of composition, with intermediate substitutions.
5. Equal-scale coordinate axes and an animated reflection across `y=x`.
6. The two-to-one square mapping, horizontal-line test, and domain restriction.
7. A numerical distinction between inverse and reciprocal.
8. Independent practice with `g(x)=3x−4`, a pause and worked solution.
9. A short visual recap.

The palette uses charcoal, warm ivory, teal and gold. The original channel
emblem is retained. Large mathematical expressions occupy the teaching canvas;
full narration sentences do not. The question-mark hook follows the explicit
checklist in the current request. The earlier independently approved script
could not be recovered; the repository's welcome and transition wording are
retained, with a new mathematical hook. The supplied YouTube reference could
not be inspected because the analysis service had insufficient credits. No
attached screenshots were available in this turn. No claim of exact matching
against those unavailable references is made.

## Preview and build

```bash
cd remotion
npm install
npm run check
npm run studio -- --no-open
# Open the InverseFunctions composition.
```

Default Studio props provide a **silent visual draft**, with estimated reading
times. Every substantial chapter also has a separate composition in the
`Inverse-scenes` folder. Final timing is computed from generated narration,
not those estimates.

After narration transfer is approved, prepare the exact authored script:

```bash
python -m pip install -r scripts/requirements-inverse.txt
python scripts/build_inverse_lesson.py --prepare-only
cd remotion
npx remotion studio src/index.ts --props=build/inverse/lesson.json --no-open
```

To produce the narrated 1920×1080 H.264 master:

```bash
python scripts/build_inverse_lesson.py
```

The narrator is locked to `en-GB-RyanNeural`, using the Day 2 settings from
`mukundacity-glitch/FPL-VORTEX-YOUTUBE-POST`. That reference repository and its
linked notebook are read-only; neither was modified.

The notebook defines baseline moods, then applies Day 2 runtime rate overrides.
The reference Day 2 profiles are intro +13% / -4 Hz; analysis +17% / -4 Hz; key
statistic +18% / 0 Hz; warning +11% / -4 Hz; outro +11% / -4 Hz. Volume stays +0%.
The maths lesson preserves that pitch and volume signature while using slower
rates: intro -3%, explanation -6%, equations/practice -10%, warning -5%, recap -3%.
`scripts/day2_ryan_settings.json` preserves both the baseline profiles and their
overrides alongside the lesson-specific rate overrides. Mapping maths chapters to those moods is an implementation choice:
opening uses intro; machine/verification/graph use analysis; algebra/practice use
key statistic; domain/notation use warning; recap uses outro.

The transport follows the tested Day 2 `edge-tts==7.2.8` setup at Microsoft's
`api.msedgeservices.com` speech endpoint. Narration is mastered with measured
two-pass EBU R128 normalization at -18 LUFS / -1.5 dBTP, LRA 7, using stereo
48 kHz, 24-bit PCM intermediates. There is no added room simulation, delay,
reverb, doubled narration or music. Listening to the complete master is still
required before calling its sound quality approved.

The provider remains the Day 2 Microsoft Edge speech service; there is no voice
or provider substitution. Only the authored maths narration is synthesized.
The reference repository and notebook are never uploaded or modified. The user
has clarified that the Day 2 voice signature must stay, with rate adapted for
premium educational pacing.

Each beat is measured with ffprobe; authentic word boundaries produce optional
SRT/VTT tracks. Audio bytes and the storyboard are hashed. Missing or partial
narration, stale speech, invalid timings or altered narration files stop the
build. Outputs are in `remotion/build/inverse/`.

## Validation and release status

```bash
cd remotion
node scripts-inverse-frames.mjs
npm run check
cd ..
python -m pytest -q
```

`node scripts-inverse-frames.mjs` renders all 60 storyboard states for inspection.
The new timeline tests cover contiguous chapters, first and last beats, stale
scripts, partial narration and the mathematical examples over multiple inputs.
The existing shell tests now assert the full-frame, sidecar-caption behavior.

The current deliverable is a visual draft and a reviewable source change.
Automatic approval review blocked external narration synthesis; the narrated
master and perceptual audio QA remain pending. The new authored lesson is
built explicitly with the command above; it does not silently replace a
published YouTube upload or republish Day 43. The scheduled publisher and its
uploaded-day locks remain intact. The shared full-frame compositor change will
apply to future hybrid lessons after this branch is merged, but it cannot
remove narration text already baked into older Manim scenes.
