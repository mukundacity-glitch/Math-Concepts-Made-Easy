import type {Node} from './timeline';
export const width = (node: Node, size: number): number => 'text' in node ?
  Math.max(size * .33, [...node.text].reduce((sum, char) => sum +
    (/[il1·()]/.test(char) ? .32 : /[=+−÷×]/.test(char) ? .78 : .57), 0) * size) + size * .11 :
  'cells' in node ? matrixWidths(node.cells, size).reduce((sum, value) => sum + value, 0) + size * .4 :
  Math.max(lineWidth(node.top, size * .82), lineWidth(node.bottom, size * .82)) + size * .4;
export const matrixWidths = (cells: readonly (readonly (readonly Node[])[])[], size: number): number[] => Array.from({length: Math.max(...cells.map((row) => row.length))}, (_, column) => Math.max(...cells.map((row) => lineWidth(row[column] ?? [], size * .72))) + size * .5);
export const lineWidth = (nodes: readonly Node[], size: number): number => nodes.reduce((sum, node) => sum + width(node, size), 0);

