# Native portrait production

The daily workflow uses `autopilot.py --hybrid`: original landscape Manim
scenes go through the verified Remotion bridge for the full lesson, and a
separate `NativeShort` composition produces the three Shorts.

Shorts never read a landscape MP4. Each uses newly rendered 840 × 960 portrait
Manim teaching boards inside a 1080 × 1920 composition at 30 FPS. The original
channel logo appears once, at top left. Equations retain TeX fraction and
inverse notation and the shared semantic palette. Complete curriculum
statements and worked steps receive dedicated narration with real word
boundaries. Captions occupy their own lane below the teaching board.

The usable horizontal region is x=80…920. The board is y=420…1380; captions
are y=1430…1630. The right interaction rail and bottom 290 pixels remain
clear. Actual Manim object bounds are checked before rendering; narrow text
wraps without ellipses. Equations that cannot remain readable stop the run
for editorial review. Complete Shorts are limited to 180 seconds and never
cut off at an arbitrary time. The production gate requires final hashes to
match native-render receipts. Speech samples are compared with each original
page track and each full-lesson chapter, using one playback channel to avoid
stereo downmix false positives.

The sole daily scheduler starts generation at 06:00 America/New_York, with
DST-aware releases at 09:00 for the full lesson and 12:00, 18:00, and 22:00
for the three Shorts. A manual first-day kickoff can schedule the main
lesson 30 minutes after upload if 09:00 has passed. Otherwise missed release
slots move to the next local day; uploads do not silently become immediate
public posts. These are target times: generation, GitHub queue delays and
YouTube processing can delay availability.

`state/upload_ledger.json` records each asset's upload intent before insertion
and its returned YouTube ID immediately afterward. Production pushes these
checkpoints before proceeding. Retries reuse completed IDs; a lost response
stops for reconciliation rather than risking a duplicate upload. The uploader
checks actual YouTube privacy and publication timestamps before advancing
the lesson counter. An uncertain receipt must be reconciled with the channel
before it is changed. The recovery workflow requires the same native proof.

Preflight: `Native portrait Shorts verification` renders all three real Day 43
Shorts without publishing, retains full videos, original audio, word timings,
and a phone-size frame for every teaching page. A successful preflight and
review precede production activation. Past uploaded days remain locked.
