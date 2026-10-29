import {width, matrixWidths, lineWidth} from './geometry';
import {useMemo, type ReactNode} from 'react';
import {useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {compileBoard, cueFrame, walkNodes, retainedRows, type BoardState, type Board, type Cue, type Node, type Row, type SpeechBeat} from './timeline';
import {boardLayout, boardThemes, wrapBoardLabel} from './theme';

const ink = boardThemes.light.ink, teal = boardThemes.light.accent;
const advance = (frame: number, start: number, duration = 10) => interpolate(frame,
  [start, start + duration], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic)});

const renderLine = (nodes: readonly Node[], center: number, baseline: number, size: number, plan: ReturnType<typeof compileBoard>, frame: number, ink: string = boardThemes.light.ink, teal: string = boardThemes.light.accent, cancellationColor: string = boardThemes.light.cancel): ReactNode => {
    let left = center - lineWidth(nodes, size) / 2;
    return nodes.map((node) => {
      const w = width(node, size), x = left + w / 2;
      left += w;
      const reveal = advance(frame, plan.frames.get(node.id) ?? Infinity);
      const cancelAt = plan.cancellations.get(node.id);
      const cancel = cancelAt === undefined || frame >= (plan.cancellationEnds.get(node.id) ?? Infinity) ? 0 : advance(frame, cancelAt, 14);
      const highlight = plan.highlights.get(node.id);
      const highlighted = highlight && frame >= highlight[0] && frame < highlight[1];
      const arrowAt = plan.arrows.get(node.id);
      const arrow = arrowAt === undefined ? 0 : advance(frame, arrowAt, 14);
      return <g key={node.id} opacity={reveal} transform={`translate(0 ${(1 - reveal) * 9})`}>
        {highlighted && <rect x={x - w / 2 - 8} y={baseline - size * .9} width={w + 16} height={size * 1.2} rx={10} fill={teal} fillOpacity={.14} stroke={teal} strokeWidth={3}/>}
        {'text' in node ? <>
          <text x={x} y={baseline} textAnchor="middle" fill={node.accent ? teal : ink}
            fontSize={size} fontFamily="Georgia, DejaVu Serif, serif">{node.text}</text>
          {cancel > 0 && <path d={`M ${x - w * .38} ${baseline + size * .12} L ${x + w * .38} ${baseline - size * .87}`}
            stroke={cancellationColor} strokeWidth={3.5} strokeLinecap="round" fill="none" pathLength={1}
            strokeDasharray={1} strokeDashoffset={1 - cancel}/>}</> : 'cells' in node ? <>{(() => {
          const columns = matrixWidths(node.cells, size);
          const top = baseline - (node.cells.length - 1) * size * .4 - size * .65;
          const bottom = baseline + (node.cells.length - 1) * size * .4 + size * .22;
          const bracket = w / 2 - 3;
          return <>
            <path d={node.determinant ? `M${x-bracket} ${top} V${bottom} M${x+bracket} ${top} V${bottom}` :
              `M${x-bracket+10} ${top} H${x-bracket} V${bottom} H${x-bracket+10} M${x+bracket-10} ${top} H${x+bracket} V${bottom} H${x+bracket-10}`} fill="none" stroke={ink} strokeWidth={3}/>
            {node.cells.flatMap((row, rowIndex) => {let cellLeft = x - (w - size * .4) / 2; return row.map((cell, column) => {
              const cellX = cellLeft + columns[column] / 2; cellLeft += columns[column];
              return <g key={`${rowIndex}-${column}`}>{renderLine(cell, cellX, baseline + (rowIndex - (node.cells.length-1)/2) * size * .8, size * .72, plan, frame, ink, teal, cancellationColor)}</g>;
            });})}
          </>;
        })()}</> : <>
          {renderLine(node.top, x, baseline - size * .40, size * .82, plan, frame, ink, teal, cancellationColor)}
          <path d={`M ${x - w / 2 + 8} ${baseline - size * .15} H ${x + w / 2 - 8}`}
            fill="none" stroke={ink} strokeWidth={2.4}/>
          {renderLine(node.bottom, x, baseline + size * .68, size * .82, plan, frame, ink, teal, cancellationColor)}
        </>}
        {arrow > 0 && <path d={`M ${x} ${baseline + size * 1.27} Q ${x - 18} ${baseline + size * .8} ${x} ${baseline + size * .28}`}
          fill="none" stroke={teal} strokeWidth={2.5} pathLength={1} strokeDasharray={1}
          strokeDashoffset={1 - arrow} markerEnd={arrow > .98 ? 'url(#arrow)' : undefined}/>}
      </g>;
    });
  };

/** Persistent working, stable token IDs, word-cued reveals and one diagonal cancellation stroke. */
export const MathBoard = ({board, beats, dark = false, states}: {board: Board; beats: readonly SpeechBeat[]; dark?: boolean; states?: readonly BoardState[]}) => {
  const palette = dark ? boardThemes.dark : boardThemes.light;
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const plan = useMemo(() => compileBoard(board, beats, fps), [board, beats, fps]);
  const active = board.filter((row) => (plan.frames.get(row.id) ?? Infinity) <= frame);
  // A rolling board retains the current step and two predecessors at readable mobile size.
  // Earlier work only leaves the viewport when a new logical line needs the space.
  const hasMatrices = board.some((row) => walkNodes(row.nodes).some((node) => 'cells' in node));
  const retained = hasMatrices ? 2 : 3;
  const visible = states ? retainedRows(board, states, beats, fps, frame) : active.slice(-(retained + 1));
  const state = states?.filter((item) => cueFrame(item.cue, beats, fps) <= frame).at(-1);
  const last = active.at(-1);
  const scroll = Math.max(0, active.length - retained - 1) + (active.length > retained ?
    advance(frame, plan.frames.get(last!.id) ?? Infinity, 20) : 0);
  return <g><defs><clipPath id="working-area"><rect x={90} y={265} width={1740} height={685}/></clipPath></defs>
    {state && <text x={112} y={245} fill={palette.accent} fontSize={36} fontFamily="Arial, sans-serif">{state.reason}</text>}
    <g clipPath="url(#working-area)">{visible.map((row) => {
    const newest = row === last;
    const size = Math.min(boardLayout.mathSize, (row.wide ? 1680 : boardLayout.mathWidth) / Math.max(1, lineWidth(row.nodes, 1)));
    if (size < 64) throw new Error('Mathematical working needs a semantic line break, not smaller text: ' + row.id);
    const labelLines = row.wide ? [row.label ?? ''] : wrapBoardLabel(row.label ?? '');
    const y = states ? 360 + visible.indexOf(row) * 175 : (hasMatrices ? 430 : boardLayout.firstBaseline) + (board.indexOf(row) - scroll) * (hasMatrices ? 280 : boardLayout.rowSpacing);
    const leaving = states ? 1 : Math.max(0, Math.min(1, 1 - (scroll - board.indexOf(row))));
    return <g key={row.id} opacity={leaving}>
      {newest && <rect x={88} y={y - 68} width={5} height={92} rx={2.5} fill={palette.accent}/>}
      <text x={boardLayout.labelX} y={row.wide ? y - 100 : y - (labelLines.length - 1) * boardLayout.labelLineHeight / 2}
        fill={palette.ink} fontSize={boardLayout.labelSize} fontWeight={600} fontFamily="Arial, sans-serif"
        opacity={advance(frame, plan.frames.get(row.id) ?? Infinity)}>
        {labelLines.map((line, lineIndex) => <tspan key={lineIndex} x={boardLayout.labelX}
          dy={lineIndex === 0 ? 0 : boardLayout.labelLineHeight}>{line}</tspan>)}
      </text>
      {renderLine(row.nodes, row.wide ? 960 : boardLayout.mathX, row.wide ? y + 20 : y, size, plan, frame, palette.ink, palette.accent, palette.cancel)}
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
