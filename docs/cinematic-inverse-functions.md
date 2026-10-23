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

Prepare the exact authored script:

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
SRT/VTT sidecar tracks. They are optional and are not embedded or burned into the video. Audio bytes and the storyboard are hashed. Missing or partial
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

The narrated master is complete: **1920×1080, 30 FPS, 8:48.133, 15,844 frames**.
A one-second waveform window from each of the 60 source narration clips was
compared against the final AAC soundtrack. The minimum waveform correlation is 0.98150; no timing offset was
detected at the verifier's 8 kHz sample resolution. The final master measures
-18.03 LUFS, with a true peak of -4.46 dBTP. It contains one stereo AAC track,
with optional captions supplied separately as SRT/VTT. Six key moments were
also extracted from the encoded master and visually checked.

The standalone builder now runs final narration-integrity verification after
rendering. Its same-channel comparison avoids stereo-downmix gain errors and
rejects doubled narration volume. Validation passed: 179 Python tests, including
actual FFmpeg mastering and AAC integrity regressions; the original 34 Remotion tests
passed during the first visual rebuild. The progressive-board update now passes
44 Remotion tests and TypeScript checking, including real cached narration cues.
The five Ryan/mastering/integrity Python regressions also pass after this update.

The new authored lesson is built explicitly with the command above. The
scheduled publisher and its uploaded-day locks remain intact; no published
YouTube upload was replaced or duplicated. The shared full-frame compositor
change applies to future hybrid lessons after merging, but cannot remove text
already baked into older Manim scenes.


## Progressive working and reusable cancellation

The algebra, both composition checks, and practice now use the shared
`remotion/src/math-board/MathBoard.tsx` renderer. Equations are expression trees
with stable term IDs and independent narration cues. The builder passes the
actual Ryan word boundaries into the render props. A number, operator or
fraction component appears at its cue, instead of displaying a complete new
answer at the start of a narration beat.

The same token renderer now also serves the function-machine calculations and
reciprocal example through `MathLine`. Diagram objects use the same word-cued
visibility helper, including sequential positive/negative inputs in the square
function example. The machine does not display its later addition operation
before that operation is introduced.

Working remains in a rolling board history. The current line and two preceding
lines stay legible; the oldest line scrolls and fades only when another line
needs the space. Existing expressions remain visible during balance operations,
with curved arrows pointing to the newly applied terms. A single diagonal coral
stroke crosses each cancelling number. The left-side subtraction remains intact
when the opposing right-side addends cancel. The two factors in a quotient are
marked separately, without crossing an entire numerator containing a sum.

The renderer contains no lesson-specific numbers, function names or beat IDs.
The two affine examples are configured in `src/inverse/models.json`; display
values and numerical checks are computed from those models. Additive cancellation
requires opposing signed values, and division requires a common nonzero factor.
The source data owns the mathematics and speech anchors; it is not safe to infer
cancellation from visually repeated digits alone. New scripts must supply anchors
that occur in their actual narration. Missing anchors, absent word boundaries,
invalid ordering, unknown targets and cancellation before a term appears stop
rendering. Silent Studio previews alone may estimate word positions.

For a future authored lesson, import `MathBoard` and provide a `Board` (rows of
atoms/fractions with word cues) plus its narrated beats. Do not copy JSX branches
for particular coefficients. Validate the complete board with `compileBoard`
before rendering. The generic renderer supports arbitrary authored expressions;
the included affine builders provide examples, rather than an automatic solver
for every topic.

`node scripts-board-review.mjs` renders twenty-two checkpoints using the actual
narrated timeline: initial reveals, balance operations, cancellations and final
numeric answers, including diagram and reciprocal reveals. The review catches symbol placement, readable working history
and clipping as well as mathematical correctness.

**Rollout:** PR #33 is still a draft and is not merged. Scheduled MP4s still use
the existing Manim-to-`PremiumLesson` route. Merging enables the shared full-frame
compositor for that route; it does not automatically translate every future
Manim lesson into this new expression-tree board. The new progressive treatment
is currently implemented and rendered for the authored inverse-functions
algebra, verification and practice chapters, and progressive operation reveals
in the machine, reciprocal and domain examples. Other topics need authored board
plans and verification before the same claim can be made for all future MP4s.
