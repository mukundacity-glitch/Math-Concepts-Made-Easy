import type {InverseProps} from '../timeline';
import {algebraBoard} from '../boards';
import {TeachingBoard} from './TeachingBoard';

const board = algebraBoard();
export const Algebra = (props: InverseProps) => <TeachingBoard {...props} board={board}
  scene="algebra" title="Build the reverse rule." chapter="03 / ALGEBRA"/>;
