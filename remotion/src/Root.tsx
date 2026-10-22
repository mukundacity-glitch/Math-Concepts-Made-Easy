import {Composition} from 'remotion';
import {ScaffoldDiagnostics} from './scaffold/ScaffoldDiagnostics';

// Phase 4, Step 1: only an isolated smoke composition is registered.
// The actual educational composition is deliberately reserved for Step 2.
export const RemotionRoot = () => (
  <Composition
    id="ScaffoldDiagnostics"
    component={ScaffoldDiagnostics}
    fps={30}
    width={1920}
    height={1080}
    durationInFrames={30}
  />
);
