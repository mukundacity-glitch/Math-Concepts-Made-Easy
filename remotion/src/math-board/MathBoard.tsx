import {useMemo, type ReactNode} from 'react';
import {useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {compileBoard, cueFrame, type Board, type Cue, type Node, type Row, type SpeechBeat} from './timeline';

const ink = '#252A2D', teal = '#087E83', coral = '#C15B48';
const advance = (frame: number, start: number, duration = 10) => interpolate(frame,
  [start, start + duration], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic)});
const width = (node: Node, size: number): number => 'text' in node ?
  Math.max(size * .33, [...node.text].reduce((sum, char) => sum +
    (/[il1·()]/.test(char) ? .32 : /[=+−÷×]/.test(char) ? .78 : .57), 0) * size) + size * .11 :
  Math.max(lineWidth(node.top, size * .82), lineWidth(node.bottom, size * .82)) + size * .4;
const lineWidth = (nodes: readonly Node[], size: number): number => nodes.reduce((sum, node) => sum + width(node, size), 0);

const renderLine = (nodes: readonly Node[], center: number, baseline: number, size: number, plan: ReturnType<typeof compileBoard>, frame: number, ink = '#252A2D', teal = '#087E83'): ReactNode => {
    let left = center - lineWidth(nodes, size) / 2;
    return nodes.map((node) => {
      const w = width(node, size), x = left + w / 2;
      left += w;
      const reveal = advance(frame, plan.frames.get(node.id) ?? Infinity);
      const cancelAt = plan.cancellations.get(node.id);
      const cancel = cancelAt === undefined ? 0 : advance(frame, cancelAt, 14);
      const arrowAt = plan.arrows.get(node.id);
      const arrow = arrowAt === undefined ? 0 : advance(frame, arrowAt, 14);
      return <g key={node.id} opacity={reveal} transform={`translate(0 ${(1 - reveal) * 9})`}>
        {'text' in node ? <>
          <text x={x} y={baseline} textAnchor="middle" fill={node.accent ? teal : ink}
            fontSize={size} fontFamily="Georgia, DejaVu Serif, serif">{node.text}</text>
          {cancel > 0 && <path d={`M ${x - w * .38} ${baseline + size * .12} L ${x + w * .38} ${baseline - size * .87}`}
            stroke={coral} strokeWidth={3.5} strokeLinecap="round" fill="none" pathLength={1}
            strokeDasharray={1} strokeDashoffset={1 - cancel}/>}</> : <>
          {renderLine(node.top, x, baseline - size * .40, size * .82, plan, frame, ink, teal)}
          <path d={`M ${x - w / 2 + 8} ${baseline - size * .15} H ${x + w / 2 - 8}`}
            fill="none" stroke={ink} strokeWidth={2.4}/>
          {renderLine(node.bottom, x, baseline + size * .68, size * .82, plan, frame, ink, teal)}
        </>}
        {arrow > 0 && <path d={`M ${x} ${baseline + size * 1.27} Q ${x - 18} ${baseline + size * .8} ${x} ${baseline + size * .28}`}
          fill="none" stroke={teal} strokeWidth={2.5} pathLength={1} strokeDasharray={1}
          strokeDashoffset={1 - arrow} markerEnd={arrow > .98 ? 'url(#arrow)' : undefined}/>}
      </g>;
    });
  };

/** Persistent working, stable token IDs, word-cued reveals and one diagonal cancellation stroke. */
export const MathBoard = ({board, beats}: {board: Board; beats: readonly SpeechBeat[]}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const plan = useMemo(() => compileBoard(board, beats, fps), [board, beats, fps]);
  const active = board.filter((row) => (plan.frames.get(row.id) ?? Infinity) <= frame);
  // A rolling board retains the current step and two predecessors at readable mobile size.
  // Earlier work only leaves the viewport when a new logical line needs the space.
  const visible = active.slice(-4);
  const last = active.at(-1);
  const scroll = Math.max(0, active.length - 4) + (active.length > 3 ?
    advance(frame, plan.frames.get(last!.id) ?? Infinity, 20) : 0);
  return <g><defs><clipPath id="working-area"><rect x={90} y={265} width={1740} height={645}/></clipPath></defs>
    <g clipPath="url(#working-area)">{visible.map((row) => {
    const newest = row === last;
    const size = Math.min(76, 1550 / Math.max(1, lineWidth(row.nodes, 1)));
    const y = 405 + (board.indexOf(row) - scroll) * 177;
    const leaving = Math.max(0, Math.min(1, 1 - (scroll - board.indexOf(row))));
    return <g key={row.id} opacity={(newest ? 1 : .57) * leaving}>
      <text x={112} y={y - 64} fill={teal} fontSize={23} fontFamily="Arial, sans-serif"
        opacity={advance(frame, plan.frames.get(row.id) ?? Infinity)}>{row.label}</text>
      {renderLine(row.nodes, 960, y, size, plan, frame)}
    </g>;
  })}</g></g>;
};


/** The same token logic can sit inside a diagram, without a rolling board layout. */
export const MathLine = ({row, beats, x = 960, y, size = 76, color = ink, accent = teal}: {
  row: Row; beats: readonly SpeechBeat[]; x?: number; y: number; size?: number; color?: string; accent?: string;
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const plan = useMemo(() => compileBoard([row], beats, fps), [row, beats, fps]);
  return <g>{renderLine(row.nodes, x, y, size, plan, frame, color, accent)}</g>;
};

/** Word-timed visibility for existing vector objects, labels and arrows. */
export const CueGroup = ({at, beats, children}: {at: Cue; beats: readonly SpeechBeat[]; children: ReactNode}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return <g opacity={advance(frame, cueFrame(at, beats, fps))}>{children}</g>;
};
