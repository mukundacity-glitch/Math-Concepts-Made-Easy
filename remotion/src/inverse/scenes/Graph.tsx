import type {InverseProps} from '../timeline';
import {Stage, Text, Arrow, colors, useBeat, ease} from '../visuals';

const point = (horizontal: number, vertical: number): [number, number] =>
  [1030 + 36 * horizontal, 850 - 36 * vertical];
export const Graph = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'graph');
  const stage = beat.stage;
  const reflection = stage === 4 ? ease(frame, 75) : stage > 4 ? 1 : 0;
  const original = Array.from({length: 81}, (_, index) => {
    const input = -3 + index / 10;
    return [input, 2 * input + 5];
  });
  const path = (swap: number) => original.map(([input, output], index) => {
    const [horizontal, vertical] = point(input * (1 - swap) + output * swap,
      output * (1 - swap) + input * swap);
    return `${index === 0 ? 'M' : 'L'} ${horizontal} ${vertical}`;
  }).join(' ');
  const [originalX, originalY] = point(3, 11);
  const [inverseX, inverseY] = point(11, 3);
  return <Stage title="Swap coordinates. Reflect the graph." chapter="05 / GEOMETRY" dark>
    <Text x={112} y={440} size={60} color={colors.mint} anchor="start" math>f(x) = 2x + 5</Text>
    {stage >= 1 && <Text x={112} y={560} size={62} color={colors.mint} anchor="start" math>(3, 11)</Text>}
    {stage >= 2 && <Text x={112} y={680} size={62} color={colors.gold} anchor="start" math>(11, 3)</Text>}
    {stage >= 5 && <Text x={112} y={805} size={55} color={colors.gold} anchor="start" math>f⁻¹(x) = (x − 5) / 2</Text>}
    {Array.from({length: 19}, (_, index) => index - 3).map((value) => {
      const [horizontal, vertical] = point(value, value);
      return <g key={value}>
        <line x1={horizontal} x2={horizontal} y1={310} y2={958} stroke="#414B50" strokeWidth={1}/>
        <line x1={922} x2={1570} y1={vertical} y2={vertical} stroke="#414B50" strokeWidth={1}/>
        {value >= 0 && value % 5 === 0 && <>
          <Text x={horizontal} y={891} size={26} color={colors.muted}>{value}</Text>
          <Text x={1000} y={vertical + 9} size={26} color={colors.muted}>{value}</Text>
        </>}
      </g>;
    })}
    <Arrow x1={922} y1={850} x2={1595} y2={850} color={colors.white}/>
    <Arrow x1={1030} y1={958} x2={1030} y2={290} color={colors.white}/>
    <Text x={1620} y={860} size={32} color={colors.white} math>x</Text>
    <Text x={1030} y={275} size={32} color={colors.white} math>y</Text>
    {stage >= 3 && <><path d="M 922 958 L 1570 310" stroke={colors.muted} strokeWidth={3}
      strokeDasharray="12 12"/><Text x={1650} y={320} size={38} color={colors.white} math>y = x</Text></>}
    <path d={path(0)} fill="none" stroke={colors.mint} strokeWidth={5} pathLength={1}
      strokeDasharray={1} strokeDashoffset={stage === 0 ? 1 - ease(frame, 60) : 0}/>
    {stage >= 4 && <path d={path(reflection)} fill="none" stroke={colors.gold} strokeWidth={5}/>}
    {stage >= 1 && <><circle cx={originalX} cy={originalY} r={11} fill={colors.mint}/>
      <Text x={originalX + 90} y={originalY - 20} size={32} color={colors.mint} math>(3, 11)</Text></>}
    {stage >= 2 && <><circle cx={inverseX} cy={inverseY} r={11} fill={colors.gold}/>
      <Text x={inverseX + 80} y={inverseY + 50} size={32} color={colors.gold} math>(11, 3)</Text></>}
    {stage >= 4 && <Arrow x1={originalX + 12} y1={originalY + 12} x2={inverseX - 12}
      y2={inverseY - 12} color={colors.gold} dashed/>}
    <Text x={112} y={970} size={32} color={colors.muted} anchor="start">
      {stage === 6 ? 'Domain ↔ range' : 'Same unit length on both axes'}
    </Text>
  </Stage>;
};
