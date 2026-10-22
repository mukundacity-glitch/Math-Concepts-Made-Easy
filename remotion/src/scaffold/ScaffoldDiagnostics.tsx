import {AbsoluteFill} from 'remotion';

/**
 * Intentional one-second build health check; NOT a lesson video.
 * The actual educational layout is introduced in Phase 4 Step 2.
 */
export const ScaffoldDiagnostics = () => (
  <AbsoluteFill
    style={{
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#081B33',
      color: '#E5E7EB',
      fontFamily: 'Arial, sans-serif',
      textAlign: 'center',
    }}
  >
    <div style={{fontSize: 64, fontWeight: 700}}>
      REMOTION SCAFFOLD READY
    </div>
    <div style={{fontSize: 27, marginTop: 24}}>
      Diagnostic composition only — lesson composition not yet implemented
    </div>
  </AbsoluteFill>
);
