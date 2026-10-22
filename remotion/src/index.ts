import {registerRoot} from 'remotion';
import {RemotionRoot} from './Root';

// The entry point must register synchronously, once.
registerRoot(RemotionRoot);
