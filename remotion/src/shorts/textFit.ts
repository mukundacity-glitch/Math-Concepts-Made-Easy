export type MeasureText = (text: string, fontSize: number) => number;

/** Wrap measured glyphs, including long unbroken metadata, without dropping text. */
export const fitShortText = (
  text: string, width: number, height: number, preferredSize: number,
  lineHeight: number, measure: MeasureText,
): {fontSize: number; lines: string[]} => {
  const words = text.trim().split(/\s+/);
  for (let fontSize = preferredSize; fontSize >= 24; fontSize--) {
    const lines: string[] = [];
    let current = '';
    for (const word of words) {
      const candidate = current ? current + ' ' + word : word;
      if (measure(candidate, fontSize) <= width) {
        current = candidate;
        continue;
      }
      if (current) lines.push(current);
      current = '';
      for (const character of word) {
        if (current && measure(current + character, fontSize) > width) {
          lines.push(current);
          current = '';
        }
        current += character;
      }
    }
    if (current) lines.push(current);
    if (lines.length * fontSize * lineHeight <= height &&
        lines.every((line) => measure(line, fontSize) <= width)) {
      return {fontSize, lines};
    }
  }
  throw new Error('Shorts text cannot fit its safe area at a readable font size');
};
