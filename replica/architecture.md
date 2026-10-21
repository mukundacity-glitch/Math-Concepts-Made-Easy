# Animation and publishing architecture

`curriculum/*.json` retains publication order and immutable published history. `curriculum/designs/catalogue.json` adds topic-keyed authored lesson designs to unpublished entries. Planning validates those designs against actual renderer models.

Narration emits timed teaching panels, each with exact math lines and visual data. The manifest carries panels and practice-pause boundaries. The audio stage synthesizes speech segments and concatenates measured silence between the question and solution. Word positions are offset across those gaps.

Remotion renders each panel from measured narration timings at 1920×1080, 30 fps. Typeset equations, coordinates, unit-circle projections, tile counts and apple counts come from explicit data. It emits the same per-scene MP4 filenames as the existing assembly, subtitle and Shorts stages.

The scheduled workflow remains at 06:00 New York production and 09:00 main-video release. Upload receipts are written immediately after each confirmed video ID. A partial package retry reuses confirmed uploads. The lesson advances only after the package upload succeeds.

The node dependencies are pinned in package-lock.json. `npm ci --prefix remotion` installs them. Manim remains available for legacy diagnostics; it is no longer the default animation engine.
