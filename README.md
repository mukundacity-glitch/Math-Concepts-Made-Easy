# Math Concepts Made Easy — Automated AI Math Teacher

Fully automated lesson factory for the **Math Concepts Made Easy** YouTube
channel. One command turns a curriculum entry into a complete, classroom-style
math video: narrated with a natural teacher voice, animated with Manim
blackboard writing, assembled with crossfades, subtitled, thumbnailed, and cut
into a vertical Short — then (once linked) posted to YouTube automatically
every day.

```
python autopilot.py            # produce the next scheduled lesson
python autopilot.py --upload   # …and post it to YouTube (after linking)
```

## How it works

```
curriculum/*.json          ← all lesson content lives here (data, not code)
        │
        ▼
pipeline/cell1_lesson.py   lesson data + 9-scene teacher narrations
pipeline/cell2_script.py   master script JSON (scenes, timing, board actions)
pipeline/cell3_audio.py    Edge-TTS voice (en-GB-Ryan) + per-word timings
pipeline/cell4_animation.py Manim renders each scene (board-write style)
pipeline/cell5_assembly.py mux + 0.3s crossfades → final MP4
pipeline/cell8_subtitles.py SRT + VTT captions from the word timings
pipeline/cell6_thumbnail.py cinematic 4K-supersampled thumbnail
pipeline/cell7_shorts.py   1080x1920 vertical Short (hook + worked example)
        │
        ▼
uploader/youtube_upload.py posts video + Short, sets thumbnail, captions,
                           playlist — metadata built from curriculum data
```

Every scene follows the fixed 9-step teaching structure (opening → hook →
concept → definition → formula → worked example → mistakes → practice →
summary) defined in `pipeline/constants.py`. **No lesson content is ever
hard-coded in the engine** — adding a grade, subject or exam track means
adding another JSON file to `curriculum/`.

## Curriculum

| File | Track | Days |
|------|-------|------|
| `curriculum/grade9.json` | Number Systems, Polynomials, Coordinate Geometry, Linear Equations, Triangles, Quadrilaterals, Circles, intro Trig, Statistics | 1–21 |
| `curriculum/grade10.json` | Quadratic Equations, Trigonometry, Sequences & Series, Sets, Limits, intro Calculus, SAT & ACT strategy | 22–40 |

Each lesson entry carries the full teaching design: goal, prerequisite,
real-world hook, concept intuition, key formula (LaTeX + spoken form),
board examples, common mistake, practice, SEO title, thumbnail angle and
playlist. The quality gate in Cell 1 refuses to build a lesson with any of
these missing, and the math-syntax check refuses malformed LaTeX.

## Running it

### Locally
```bash
pip install -r requirements.txt
sudo apt-get install ffmpeg libcairo2-dev libpango1.0-dev \
     texlive texlive-latex-extra texlive-fonts-recommended dvipng cm-super

python autopilot.py                 # next scheduled day (state/progress.json)
python autopilot.py --day 7         # a specific day
python autopilot.py --from-stage 4  # resume after a failed render
```
Output goes to `output/` (override with `MCME_OUTPUT_DIR=/path`).
Optional branding: put your banner at `output/2.png` and logo at
`output/assets/logo.png`.

### In Google Colab
Clone the repo and run `python autopilot.py` — Google Drive is mounted
automatically and everything is written to `MyDrive/Math-9`, same as the
original notebook.

### Automatically, every day (GitHub Actions)
`.github/workflows/daily-video.yml` produces the next lesson every day at
12:30 UTC. It is **off by default**; flip it on with one repository
variable: `Settings → Secrets and variables → Actions → Variables →
AUTOPILOT_ENABLED = true`. Finished videos are attached to each workflow
run as artifacts, and `state/progress.json` is committed back so the day
counter always advances.

## Linking your YouTube channel (later — one-time setup)

The pipeline is fully usable before linking; uploads simply skip with a
warning until these steps are done.

1. In [Google Cloud Console](https://console.cloud.google.com) create a
   project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen (External, add your Gmail as a test
   user), then create an **OAuth client ID → Desktop app** and save the
   downloaded file as `secrets/client_secret.json`.
3. On your own computer run `python -m uploader.authorize`, sign in with
   the channel's Google account, and allow access — this writes
   `secrets/token.json`.
4. Test without posting: `python -m uploader.youtube_upload --day 1 --dry-run`
5. Real uploads start as **private** so you can review them. When happy,
   set `YT_PRIVACY=public`.
6. For daily auto-posting from GitHub Actions, paste the contents of the
   two files into repository **secrets** `YT_CLIENT_SECRET_JSON` and
   `YT_TOKEN_JSON`, and add the variable `YT_PRIVACY = public`.

`secrets/` is git-ignored — credentials never enter the repository.

## Repo layout

```
autopilot.py          one-command daily producer + day tracking
curriculum/           lesson content (JSON, one file per grade/track)
pipeline/             the 8 production stages + shared paths/constants
uploader/             YouTube posting + one-time authorize helper
state/progress.json   which day runs next, what's done, what's uploaded
legacy/               original Colab notebook export (frozen reference)
.github/workflows/    daily automation (opt-in)
```

## Roadmap

- [ ] Day-2 review videos (homework solutions + quiz) per topic
- [ ] Practice-sheet PDF generator into `practice_sheets/`
- [ ] Grade-level expansion: more Grade 10 depth, SAT course track
- [ ] Community-post announcements alongside each upload
