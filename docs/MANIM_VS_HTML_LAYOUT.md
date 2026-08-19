# Manim is not HTML/CSS — why text overlapped

## HTML/CSS
- Flow layout: block/flex/grid
- Text wraps automatically
- Overlap is rare unless `position:absolute` collides

## Manim
- Every mobject has an absolute center `(x, y, z)` in the scene
- `next_to`, `move_to`, `arrange` only set coordinates once
- There is **no** reflow when a sibling grows
- `scale_to_fit_height()` on a **group of many lines** shrinks everything until labels sit on top of each other — looks like “overlap”

## Bugs we hit
1. **Hook scene** stacked a new diagram every sentence, then `scale_to_fit_width(12.6)` crushed them.
2. **Concept scene** laid out *all* narration beats, then `scale_to_fit_height(4.3)` crushed text.
3. **Worked board** packed every example line into one card and scaled the whole stack down.
4. **V2 triangle** used `next_to` on sides with long strings (`opp = sin θ`) and no side lengths — labels collided and looked like “triangle with no data”.

## ENGINE_VISUAL_V3 rules
- One main visual at a time on hook
- At most 2 concept sentences visible; page if needed
- Worked examples paginate at board bottom — never global crush
- Triangle labels sit on **exterior anchors** with real numbers (3–4–5)
