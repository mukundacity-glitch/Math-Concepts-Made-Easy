# Posted-video lock policy

Videos **1–21 are already posted and are immutable by default**.

- `pipeline.paths.MIN_OPEN_DAY` is `22`.
- `state/progress.json` starts the open sequence at Day 22.
- Normal production and upload commands reject any earlier day.
- The daily workflow never supplies the emergency override.

`--allow-locked-day` exists only for a deliberate, owner-approved recovery. It
must not be used for bulk regeneration or replacement uploads.
