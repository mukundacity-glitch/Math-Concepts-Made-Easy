import type {InverseProps} from '../timeline';
import {practiceBoard} from '../boards';
import {TeachingBoard} from './TeachingBoard';

const board = practiceBoard();
export const Practice = (props: InverseProps) => <TeachingBoard {...props} board={board}
  scene="practice" title="Your turn. Find the way back." chapter="08 / YOUR TURN"/>;
