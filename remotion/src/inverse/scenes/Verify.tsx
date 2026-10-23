import type {InverseProps} from '../timeline';
import {verificationBoard} from '../boards';
import {TeachingBoard} from './TeachingBoard';

const board = verificationBoard();
export const Verify = (props: InverseProps) => <TeachingBoard {...props} board={board}
  scene="verify" title="A round trip returns the input." chapter="04 / VERIFY"/>;
