# Cinematic lesson production

`CinematicLesson` is the default full-video renderer. The daily workflow runs it
at 06:00 America/New_York, verifies the encoded media, then schedules YouTube
publication for 09:00 local time. The paired UTC schedules account for daylight
saving time. Existing upload receipts and posted-day locks prevent duplicates;
progress advances only after upload succeeds. Recovery publishing requires the
same cinematic QA receipt as the normal daily path.

## Readability and progressive working

The 1920×1080 canvas is entirely the teaching image. Warm ivory uses charcoal
mathematics and deep teal accents; dark slate uses ivory mathematics and bright
mint accents. Teaching labels are 42px, medium-weight, and retain full contrast
when earlier working stays on the board. Equations start at 90px and may never
shrink below 64px. Wide expressions receive the complete teaching width or split
at mathematical boundaries; unsupported crowded layouts stop production.

The channel name is 38px bold in two colors, with an 84px emblem. Each number and
operator appears on its actual narrated word cue. Previous steps remain visible
in a rolling history. Verified additive inverses and common nonzero factors get
single diagonal cancellation strokes. Missing cues or unsafe cancellation cannot
silently produce a finished lesson.

`pipeline/cinematic_content.py` compiles the curriculum's formulas, worked
examples, mistakes, and practice into expression trees. Fractions and matrices
retain their structure. Function graphs use restricted symbolic parsing and
computed coordinates with equal axis scales. The compiler does not select
lesson-specific JSX or substitute fixed example coefficients. The remaining
87 curriculum lessons, starting at Day 44, pass the board/cue geometry audit.
The next lesson includes an explicit neither-even-nor-odd counterexample and
independent practice, in addition to the two symmetry rules.

The standalone `InverseFunctions` composition remains available as the complete
8:48 authored inverse-functions lesson. It uses the same readable board and
branding. Its 60 narration segments have been checked against the final encoded
soundtrack. Caption tracks are optional SRT/VTT files, never board text.

## Ryan narration

The voice remains `en-GB-RyanNeural` with the Day 2 pitch/volume signature from
the read-only `FPL-VORTEX-YOUTUBE-POST` reference. That repository was not changed.
`scripts/day2_ryan_settings.json` records the reference settings and slower
educational rate overrides: opening/recap −3%, explanation −6%, working −10%,
and warnings −5%. No voice or provider fallback is permitted.

The tested transport is `edge-tts==7.2.8`. Audio uses measured two-pass EBU R128
normalization at −18 LUFS, a −1.5 dBTP ceiling, and stereo 48kHz PCM24
intermediates. A measured static gain correction handles short-clip gating
variation without changing timing; it fails if the approved peak ceiling would
be exceeded. No echo, reverb, music, or duplicate narration is added. Native
portrait Shorts reuse the same Ryan profiles and mastering.

## Commands

```bash
python -m pip install -r requirements.txt
cd remotion
npm install
npm run check
npx remotion browser ensure
cd ..
python -m pytest -q
python -m pipeline.cinematic_lesson --audit
python autopilot.py --no-advance          # next complete media package
python -m pipeline.cinematic_lesson --day 44  # full-video render only
python scripts/build_inverse_lesson.py       # authored inverse-functions master
```

`--cinematic` explicitly selects the default route. `--legacy-renderer` is for
local review of older layouts and cannot publish through autopilot.

Generated masters, optional captions, and `Day_NNN_cinematic-qa.json` receipts
are under `output/final_videos/`. The receipt binds the encoded video SHA256 to
its verified narration count, frame dimensions, and readability requirements.
Missing, partial, or stale receipts block scheduled and recovery publishing.
Actual narration boundaries and audio hashes are checked before rendering;
waveform windows from every source beat are compared against final AAC audio.
Boards, timing, contrast, cue ordering, cancellation structure, matrices, safe
graphs, and upload-gate failures have regression coverage.

For visual review, `remotion/scripts-cinematic-review.mjs` renders the end of
each chapter from real narration props. `scripts-board-review.mjs` covers the
authored inverse lesson's intermediate reveals and cancellations. Silent Studio
previews estimate word positions; production requires actual word boundaries.
