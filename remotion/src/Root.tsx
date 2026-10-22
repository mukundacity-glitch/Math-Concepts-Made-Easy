import {Composition} from 'remotion';
import {ScaffoldDiagnostics} from './scaffold/ScaffoldDiagnostics';

// Phase 4, Step 1: only an isolated smoke composition is registered.
// Step 2 will introduce PremiumLesson. No live uploader imports Remotion.
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
