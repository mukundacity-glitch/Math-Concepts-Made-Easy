import {lineWidth} from '../math-board/geometry';
import {wrapBoardLabel} from '../math-board/theme';
import {compileBoard, cueFrame, type Board, type Cue, type SpeechBeat} from '../math-board/timeline';
export type Point = {readonly x: number; readonly y: number};
export type Diagram = {readonly kind: 'function'; readonly equation: string;
  readonly points: readonly (Point | null)[]; readonly samples: readonly Point[]; readonly sampleCues?: readonly Cue[]};
export type Chapter = {readonly id: string; readonly title: string; readonly dark: boolean;
  readonly beats: readonly SpeechBeat[]; readonly board: Board; readonly diagram?: Diagram | null};
export type CinematicProps = {readonly schemaVersion: string; readonly day: number;
  readonly title: string; readonly chapters: readonly Chapter[]};
export const chapterDuration = (chapter: Chapter) => chapter.beats.reduce((sum, beat) => sum + beat.durationInFrames, 0);

export const cinematicFrames = (props: CinematicProps): number => {
  if (props.schemaVersion !== 'cinematic-v1' || !Number.isSafeInteger(props.day) || props.day < 1 ||
    !props.title.trim() || !props.chapters.length) throw new Error('Invalid cinematic lesson');
  const ids = new Set<string>();
  for (const chapter of props.chapters) {
    if (ids.has(chapter.id) || !chapter.beats.length) throw new Error('Missing or duplicate chapter');
    ids.add(chapter.id);
    for (const beat of chapter.beats) {
      if (!Number.isSafeInteger(beat.durationInFrames) || beat.durationInFrames < 15 || !beat.speech.trim()) throw new Error('Invalid narrated beat');
      if (beat.audioSrc && (!/^cinematic\/day-\d+\/[a-z0-9-]+\.wav$/.test(beat.audioSrc) || !beat.words?.length || !/^[a-f0-9]{64}$/.test(beat.audioSha256 ?? ''))) {
        throw new Error('Unverified cinematic narration');
      }
    }
    compileBoard(chapter.board, chapter.beats, 30);
    for (const row of chapter.board) {
      if (!row.wide) wrapBoardLabel(row.label ?? '');
      if ((row.wide ? 1680 : 1090) / Math.max(1, lineWidth(row.nodes, 1)) < 64) throw new Error('Unreadably small mathematical row: ' + row.id);
    }
    if (chapter.beats.some((beat) => beat.audioSrc) && chapter.beats.some((beat) => !beat.audioSrc)) throw new Error('Partial narration cannot render');
    if (chapter.diagram) {
      for (const cue of chapter.diagram.sampleCues ?? []) cueFrame(cue, chapter.beats, 30);
      if (chapter.diagram.kind !== 'function' || chapter.diagram.points.some((point) =>
        point !== null && (!Number.isFinite(point.x) || !Number.isFinite(point.y)))) throw new Error('Invalid computed graph');
    }
  }
  return props.chapters.reduce((sum, chapter) => sum + chapterDuration(chapter), 0);
};

