/** Contrast is selected for the canvas; teaching text never inherits a dimmed row. */
export const boardThemes = {
  light: {background: '#F4F0E7', ink: '#172A35', accent: '#006A70', secondary: '#344F58', cancel: '#AF392B'},
  dark: {background: '#20262B', ink: '#FFFDF4', accent: '#63EED7', secondary: '#E2E8E7', cancel: '#FF9C87'},
} as const;
export const boardLayout = {
  labelX: 112, labelWidth: 490, labelSize: 42, labelLineHeight: 51,
  mathX: 1255, mathWidth: 1090, mathSize: 90,
  firstBaseline: 390, rowSpacing: 210,
} as const;
export const wrapBoardLabel = (label: string): string[] => {
  const lines: string[] = [];
  for (const word of label.split(/\s+/).filter(Boolean)) {
    const last = lines.at(-1);
    if (!last || (last + ' ' + word).length > 22) lines.push(word);
    else lines[lines.length - 1] += ' ' + word;
  }
  if (lines.length > 3) throw new Error('Teaching label must be concise enough for three readable lines');
  return lines;
};
