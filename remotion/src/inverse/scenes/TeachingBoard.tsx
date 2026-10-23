import {useMemo} from 'react';
import {MathBoard} from '../../math-board/MathBoard';
import type {Board} from '../../math-board/timeline';
import type {InverseProps, SceneName} from '../timeline';
import {Stage} from '../visuals';

export const TeachingBoard = ({beats, board, scene, title, chapter}: InverseProps & {
  board: Board; scene: SceneName; title: string; chapter: string;
}) => {
  const chapterBeats = useMemo(() => beats.filter((beat) => beat.scene === scene), [beats, scene]);
  return <Stage title={title} chapter={chapter}><MathBoard board={board} beats={chapterBeats}/></Stage>;
};
