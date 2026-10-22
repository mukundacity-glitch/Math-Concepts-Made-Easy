/**
 * Composition-shell brand tokens only.
 * Never color mathematical symbols here. Manim's semantic_math.py is the
 * authoritative variable/operator/exponent palette and remains untouched.
 */
export const theme = {
  canvas: '#081B33',
  deep: '#09162B',
  surface: '#102C57',
  surfaceRaised: '#152E4F',
  stroke: '#315576',
  accent: '#FACC15',
  signal: '#22D3EE',
  text: '#F5F8FF',
  subdued: '#B5C6DC',
  quiet: '#8199B8',
  shadow: 'rgba(0, 0, 0, 0.34)',
  font: 'Arial, Helvetica, sans-serif',
  horizontalSafe: 96,
  verticalSafe: 64,
} as const;

export const lessonCanvas = {
  width: 1920,
  height: 1080,
  fps: 30,
} as const;
