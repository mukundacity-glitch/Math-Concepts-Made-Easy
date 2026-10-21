# Mathematics lesson redesign

## Sources and scope

| Source | Use |
|---|---|
| https://www.3blue1brown.com/lessons/neural-networks/ | Reference progression from a familiar problem to linked visual representations and formal notation |
| https://www.youtube.com/watch?v=aircAruvnKk | User-selected reference, not a source of copied code, narration, music or assets |
| Existing curriculum JSON | Preserve topic order, published-day locks and mathematical content |
| Existing daily workflow run 39440597010 | Day 42 practice rendering failed before any upload |

The original engineering and narration in this change are specific to this repository. No source code, frames, music or branding were taken from the reference.

## Teaching sequence

A topic-specific opening poses a problem. An explicit model explains the intuition. Three worked problems connect representations. A misconception is corrected. Six independent practice prompts each precede silent thinking time and a worked answer. The closing transfers the idea to a fresh problem.

## Data contract

Numerical visual data is authoritative: object groups contain integer counts; graph series contain explicit finite points; function machines declare inputs and outputs. The engine never invents an unimplemented renderer from a string name.

## Current content coverage

Eight authored chapter designs cover Grades 9–12: composite functions, inverse functions, even/odd functions, function transformations, unit circle, derivative, shopping equations and quadratic area models. The other 124 existing entries use the new renderer/narration path with their existing board content. They have **not** all received three new worked examples and six new questions. `python -m pipeline.audit` reports this distinction; a renderer upgrade is not a completed curriculum rewrite.
