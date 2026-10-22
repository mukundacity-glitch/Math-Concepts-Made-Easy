# Phase 2 — verified educational lesson contract

This phase defines **what a complete, independently checked lesson must
contain**. It does not yet claim that the existing nine-stage Manim renderer
can show 10 independent examples and 15 practice solutions in the video.

## One-by-one execution sequence

1. **Preserve production:** keep `main`, `state/progress.json`, historical
   curriculum entries, and both YouTube workflows unchanged.
2. **Identify concepts:** each upgraded entry receives a stable `concept_id`.
   Legacy lessons receive an implicit `day-XXX` ID without rewriting history.
3. **Declare prerequisites:** use `prerequisite_ids` rather than free-text
   only. Validate every reference exists and precedes the new lesson.
4. **Create a structured learning contract:** opt in using
   `educational_content.schema_version: "2.0"`, at least two learning
   objectives, and a documented answer delivery mode.
5. **Require at least 10 distinct worked examples:** each stores
   `id`, `prompt`, `difficulty`, `format`, independently checked
   `answer`, `check`, and at least two explained mathematical `steps`.
6. **Require at least 15 distinct practice questions:** the same structured
   fields, three difficulty tiers, and verified steps/answers.
7. **Verify actual math, not labels:** supported first-slice checks are
   `linear_equation`, `equivalent_expression`, and `evaluate`.
   All intermediate mathematical states must preserve the expected result.
   Arbitrary Python expressions, function calls, and unsupported math fail.
8. **Provide the promised answers:** each upgraded lesson includes an
   `answer_delivery` destination. The sample includes a real companion
   answer file containing all 25 worked solutions and practice answers.
9. **Integrate with existing pipeline:** validate opt-in lessons during Cell 1,
   copy structured content into Cell 2's timed script, and validate again in
   scene QA. Legacy lessons stay compatible.
10. **Test corruption and regression:** malformed equations, fabricated
    answers, invalid intermediate states, duplicate prompts, insufficient
    counts and incorrect prerequisite references must fail closed.
11. **Review and verify CI:** the phase-2 branch is stacked on phase 1.
12. **Only after the renderer supports all 25 items**, gradually migrate
    real future curriculum lessons, produce a complete rendered sample,
    visually inspect it, and promote the feature. **Do not flip daily
    publishing over during this data-contract phase.**

## Schema fragment

```json
{
  "concept_id": "g9.linear-equations",
  "prerequisite_ids": ["day-001"],
  "educational_content": {
    "schema_version": "2.0",
    "learning_objectives": [
      "Solve a one-variable linear equation.",
      "Check the answer by substitution."
    ],
    "answer_delivery": {
      "mode": "companion",
      "resource_id": "answers/lesson-xxx.md"
    },
    "worked_examples": [
      {
        "id": "W01",
        "prompt": "Solve 3*x+5=20.",
        "difficulty": "foundation",
        "format": "algebra",
        "check": {"kind": "linear_equation", "input": "3*x+5=20"},
        "steps": [
          {"explanation": "Subtract five from both sides.", "math": "3*x=15"},
          {"explanation": "Divide both sides by three.", "math": "x=5"}
        ],
        "answer": "5"
      }
    ],
    "practice_questions": []
  }
}
```

The fragment illustrates the shape only; fewer than 10/15 fails validation.
A complete **nonproduction** working demonstration and full companion
solutions are supplied in `examples/premium_algebra_lesson.json` and
`examples/premium_algebra_answers.md`. All verification logic is reusable
and does not hard-code the fixture's answers in renderer components.

## Limitations and nonclaims

- This phase verifies structured **content mathematics**, not the spoken
  explanation's pedagogy, visual object truth, or final MP4 quality.
- Schema-2 math verification initially supports exact arithmetic and one
  variable (`x`) for linear equations, expression equivalence, and
  substitution. Unsupported topics must gain new independent math
  verifiers before their production lessons can use v2.
- The first model ensures mathematical equivalence of states. It does not
  verify whether the wording of a word problem exactly encodes the stated
  equation; that still needs authoring review and semantic QA.
- The current renderer caps worked board lines and has nine compatibility
  scenes. The 10/15 contract must not be advertised as fully delivered
  onscreen until the rendering phase supports pagination/scene splitting
  with synchronised narrated solutions.
- None of the existing current lessons was silently promoted to schema 2.
  No Shorts, video, upload, credential, progress, or scheduling changes
  are included.

## Production-readiness gate

A lesson is eligible for opt-in production only when: (1) its 25 separate
questions pass independent mathematical validation, (2) the renderer
actually displays all required content at readable size and timing,
(3) a real render receives frame and audio review, (4) its companion
answers are deliverable, and (5) the publishing retry system has
asset-level idempotency protections. Remaining work is carried forward
to the next reviewable phases.


## Cross-cell proof and Remotion boundary

The opt-in schema-2 fields must be copied from Cell 1's curriculum entry
into its generated `cell1_config.py`. The script-builder (Cell 2) then
propagates the exact same verified content into the lesson script. New
tests enforce this so no pre-render adapter can silently discard the
10 worked examples or 15 practice questions. Scene-script QA again
validates the concept ID, prerequisites and all 25 answer sets.

**Remotion is intentionally not added during Phase 2.** Per the existing
architecture, Manim remains responsible for computing and validating
mathematical diagrams. A later Remotion phase will compose those clips,
captions and premium layouts on a synchronized timeline. This avoids
creating a second scheduler, alternative math truth source or competing
YouTube publishing workflow.

A reusable clean vertical slice and regression-first checks, following
the Replica Toolkit engineering workflow, are in
`examples/premium_algebra_lesson.json`,
`examples/premium_algebra_answers.md` and
`tests/test_lesson_contract.py`.
