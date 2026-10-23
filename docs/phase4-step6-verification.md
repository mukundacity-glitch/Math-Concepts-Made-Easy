# Phase 4 Step 6 — completed verification

The real nine-scene Manim–Remotion demonstration is implemented, rendered, verified and merged in [PR #30](https://github.com/mukundacity-glitch/Math-Concepts-Made-Easy/pull/30). Remotion production rollout remains disabled.

## Reproducible evidence

- [Successful full demo workflow](https://github.com/mukundacity-glitch/Math-Concepts-Made-Easy/actions/runs/39898135294)
- [Successful independent export review](https://github.com/mukundacity-glitch/Math-Concepts-Made-Easy/actions/runs/39900502546)
- [Complete videos, source media and verification pack](https://github.com/mukundacity-glitch/Math-Concepts-Made-Easy/actions/runs/39900502546/artifacts/12479332028), retained for 90 days.
- [Mathematical render QA](https://github.com/mukundacity-glitch/Math-Concepts-Made-Easy/actions/runs/39898135255)
- [Phase 3 render regression](https://github.com/mukundacity-glitch/Math-Concepts-Made-Easy/actions/runs/39898135267)

The successful full demo tested runtime source `ecd217214c921cbfe2881d05f8a21f7916406434`. The final PR head `3de0a024375157cd769d30118d7cc184d03b1bd0` adds only the independent review workflow and script. A GitHub compare confirmed that delta; the independent job also checks the exported renderer's SHA-256 against its checkout. The merge commit is `d768d086c75a523dd751de2129691bef07a01030`. This documentation update changes no runtime code.

## Failures resolved

| Failure | Before | After |
| --- | --- | --- |
| Native package setup | Two timed attempts used the same slow Azure mirror; the job exited 124. | Bounded retries and a real fallback to signed Ubuntu standard/security archives; FFmpeg, FFprobe, Cairo and Pango are checked after installation. |
| Production protection after an early failure | Preparation had not written the baseline, so the always-run check raised FileNotFoundError. | Capture the baseline immediately after checkout with Python's standard library. Preparation validates it instead of replacing it. |
| Concept text during a transition | The departing sentence faded out while the remaining stack moved into the same space. | Remove the departing sentence before restacking; retain the two-sentence limit and original narration timing. |
| Empty evidence upload | The artifact step could succeed while uploading nothing. | Missing evidence is an upload error. |

Three behavioral tests cover protection after an installation failure, unchanged repeated capture, and rejection of a changed protected file without overwriting its baseline.

## Complete-run results

- **154 Python tests passed**, with no skips in the full media runtime.
- **31 Remotion tests passed**, with zero failures; TypeScript/composition checks completed.
- All **10 worked examples and 15 practice questions** passed mathematical verification.
- All nine authentic Manim scenes and original generated narration tracks were rendered.
- Original media hashes and complete caption coverage were verified.
- Final dimensions, frame rate, frame count, duration and single narration stream passed.
- All nine chapter audio comparisons and production-state protection passed.
- An independent download verified the artifact/MP4 hashes and renderer provenance.

| Output | Resolution | FPS | Frames | Duration |
| --- | --- | --- | --- | --- |
| Full lesson | 1920 × 1080 | 30 | 35003 | 1166.767 s (19 min 26.767 s) |
| Formula Short | 1080 × 1920 | 30 | 914 | 30.467 s |

Final MP4 SHA-256:

- Full lesson: `2b65400f5ceb6fd4f49973014dfed58ecb1d1871053949d310100f911ce5c8ee`
- Formula Short: `f3e3775d0416e390f810f4deb700eb9e2573644f2d69899366d312b470169175`
- Final reviewed evidence ZIP: `9b744d3ce43324be4239ad55b0021a18ef7b290909e04ecc53eccae015d7c73d`

## Chapter audio and captions

The final verifier compares a decoded two-second window in each chapter with its original narration, checks left/right playback channels, and allows only bounded codec/frame rounding. It tests real playback channels rather than FFmpeg's synthetic stereo-to-mono downmix. There are **407 caption pages** across the nine chapters.

| Scene | Stage | Duration, s | Caption pages | Speech correlation | Speech gain |
| --- | --- | --- | --- | --- | --- |
| 1 | opening | 35.967 | 12 | 0.997580 | 0.997114 |
| 2 | hook | 26.500 | 11 | 0.994446 | 1.003312 |
| 3 | concept | 38.733 | 15 | 0.998388 | 0.999128 |
| 4 | definition | 32.833 | 12 | 0.996081 | 1.000696 |
| 5 | formula | 26.467 | 9 | 0.998884 | 0.999045 |
| 6 | worked_example | 360.100 | 123 | 0.999420 | 0.997509 |
| 7 | mistakes | 40.633 | 16 | 0.997892 | 0.999478 |
| 8 | practice | 556.700 | 192 | 0.980033 | 1.016033 |
| 9 | summary | 44.833 | 17 | 0.999393 | 0.998140 |

The independent review additionally checked the Short against the original formula narration at source offsets 0.500 s and 13.233 s. Correlations were 0.998885 and 0.998483, with gains 0.999044 and 0.998512. Both playback channels agreed within the verifier's tolerance.

## Rendered-frame review

The assistant inspected actual exported PNGs, not mockups:

- All nine chapter review frames in `all-nine-chapters.png`.
- `concept-transition-review.png` at 55% of the concept chapter: the previously overlapping sentences are now separated/removed correctly.
- `short-phone-360.png` at 360 × 640: the main equation is readable, the original logo is present, and captions occupy their own lane outside the mathematical panel.

Semantic mathematical colors and uncropped mathematical visuals remain in the sampled frames. Sequential reveals can leave a panel empty before its narrated reveal; that is distinct from a missing chapter.

This is sampled rendered-frame inspection and sampled audio comparison, not a frame-by-frame viewing or word-by-word listening audit of the entire lesson. No physical phone playback session or YouTube upload was performed.

## Production boundary

The demo uses lesson 999 and does not call the uploader or advance production progress. Before/after hashes match for progress, creative history, autopilot, daily publishing, recovery publishing and the existing Shorts pipeline.

A fresh post-merge read confirms repository state still records lessons 1–42 as uploaded/locked and `next_day: 43`. This is repository state, not an independent audit of YouTube listings. The existing publishing schedule is unchanged. The shared Manim readability fix applies to future renders; existing uploaded videos are unchanged.

**Phase 4 Step 6 is complete.** Production integration/activation remains outside this verification change and has not been enabled.

## Reuse the independent review

The manual `Phase 4 Step 6 — Export Evidence Review` workflow accepts a successful demo `run_id`. It downloads that run's artifact, verifies its digest/source identity, checks Short narration, extracts review frames and retains the package. Its PR verification is pinned to the successful run above so the record does not silently switch to unrelated newer media.
