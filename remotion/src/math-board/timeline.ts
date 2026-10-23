/** A lesson-independent board contract. Cues refer to spoken words, never seconds. */
export type Word = {readonly text: string; readonly start: number; readonly end: number};
export type SpeechBeat = {readonly id: string; readonly speech: string;
  readonly durationInFrames: number; readonly audioSrc?: string; readonly audioSha256?: string; readonly words?: readonly Word[]};
export type Cue = {readonly beat: string; readonly phrase: string; readonly occurrence?: number;
  readonly edge?: 'start' | 'end'};
export type Atom = {readonly id: string; readonly text: string; readonly cue?: Cue;
  readonly accent?: boolean; readonly cancel?: Cue};
export type Fraction = {readonly id: string; readonly top: readonly Node[];
  readonly bottom: readonly Node[]; readonly cue?: Cue};
export type Matrix = {readonly id: string; readonly cells: readonly (readonly (readonly Node[])[])[]; readonly determinant?: boolean; readonly cue?: Cue};
export type Node = Atom | Fraction | Matrix;
export type Row = {readonly id: string; readonly cue: Cue; readonly nodes: readonly Node[];
  readonly label?: string; readonly wide?: boolean; readonly arrows?: readonly {readonly target: string; readonly cue: Cue}[]};
export type Board = readonly Row[];

const normalize = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');

/** Silent previews may estimate boundaries. Narrated renders must supply real boundaries. */
export const cueFrame = (cue: Cue, beats: readonly SpeechBeat[], fps: number): number => {
  const index = beats.findIndex((beat) => beat.id === cue.beat);
  if (index < 0) throw new Error('Unknown cue beat: ' + cue.beat);
  const beat = beats[index];
  if (beat.audioSrc && !beat.words?.length) throw new Error('Missing real word boundaries: ' + beat.id);
  const words = beat.words ?? beat.speech.split(/\s+/).map((text, i, all) => ({
    text, start: i * Math.max(1, beat.durationInFrames / fps - 1) / all.length,
    end: (i + 1) * Math.max(1, beat.durationInFrames / fps - 1) / all.length,
  }));
  const target = cue.phrase.split(/\s+/).map(normalize).filter(Boolean);
  if (!target.length) throw new Error('Empty narration cue');
  const matches = words.flatMap((_, start) => target.every((token, i) =>
    normalize(words[start + i]?.text ?? '') === token) ? [start] : []);
  const occurrence = cue.occurrence ?? 0;
  if (!Number.isSafeInteger(occurrence) || occurrence < 0 || matches[occurrence] === undefined) {
    throw new Error('Narration cue absent: ' + cue.beat + ' / ' + cue.phrase);
  }
  const word = words[matches[occurrence] + (cue.edge === 'end' ? target.length - 1 : 0)];
  if (!Number.isFinite(word.start) || !Number.isFinite(word.end) || word.start < 0 ||
    word.end < word.start || word.end * fps > beat.durationInFrames) throw new Error('Invalid word boundary');
  const offset = beats.slice(0, index).reduce((sum, item) => sum + item.durationInFrames, 0);
  return offset + Math.round((cue.edge === 'end' ? word.end : word.start) * fps);
};

export const walkNodes = (nodes: readonly Node[]): Node[] => nodes.flatMap((node) =>
  'text' in node ? [node] : 'cells' in node ? [node, ...node.cells.flatMap((row) => row.flatMap((cell) => walkNodes(cell)))] : [node, ...walkNodes(node.top), ...walkNodes(node.bottom)]);

export const compileBoard = (board: Board, beats: readonly SpeechBeat[], fps: number) => {
  if (!Number.isFinite(fps) || fps <= 0 || new Set(beats.map((beat) => beat.id)).size !== beats.length) {
    throw new Error('Invalid narration clock or duplicate beat IDs');
  }
  for (const beat of beats) {
    if (!Number.isSafeInteger(beat.durationInFrames) || beat.durationInFrames <= 0) throw new Error('Invalid beat duration');
    let previousEnd = 0;
    for (const word of beat.words ?? []) {
      if (!word.text || !Number.isFinite(word.start) || !Number.isFinite(word.end) ||
        word.start < previousEnd - .001 || word.end < word.start || word.end * fps > beat.durationInFrames) {
        throw new Error('Invalid or reordered word boundaries: ' + beat.id);
      }
      previousEnd = word.end;
    }
  }
  const frames = new Map<string, number>();
  const cancellations = new Map<string, number>();
  const arrows = new Map<string, number>();
  let previous = -1;
  for (const row of board) {
    if (frames.has(row.id)) throw new Error('Duplicate board ID: ' + row.id);
    const start = cueFrame(row.cue, beats, fps);
    if (start < previous) throw new Error('Board rows must follow narration order');
    previous = start;
    frames.set(row.id, start);
    const visit = (nodes: readonly Node[], parentStart: number) => {
      for (const node of nodes) {
        if (frames.has(node.id)) throw new Error('Duplicate board ID: ' + node.id);
        const reveal = node.cue ? cueFrame(node.cue, beats, fps) : parentStart;
        if (reveal < parentStart) throw new Error('A token cannot precede its row or fraction: ' + node.id);
        frames.set(node.id, reveal);
        if ('text' in node && node.cancel) {
          const cancel = cueFrame(node.cancel, beats, fps);
          if (cancel < reveal) throw new Error('Cannot cancel an unseen term');
          cancellations.set(node.id, cancel);
        }
        if ('cells' in node) {for (const row of node.cells) for (const cell of row) visit(cell, reveal);}
        else if ('top' in node) {visit(node.top, reveal); visit(node.bottom, reveal);}
      }
    };
    visit(row.nodes, start);
    for (const arrow of row.arrows ?? []) {
      if (!walkNodes(row.nodes).some((node) => node.id === arrow.target)) throw new Error('Unknown operation target');
      const when = cueFrame(arrow.cue, beats, fps);
      if (when < (frames.get(arrow.target) ?? start)) throw new Error('Arrow targets an unseen term');
      arrows.set(arrow.target, when);
    }
  }
  return {frames, cancellations, arrows};
};
