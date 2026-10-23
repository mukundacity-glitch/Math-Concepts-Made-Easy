import {useMemo, type ReactNode} from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {InverseProps} from '../timeline';
import {Stage, Text, Arrow, colors, useBeat, Footer} from '../visuals';
import {CueGroup, MathLine} from '../../math-board/MathBoard';
import {cueFrame, type Cue} from '../../math-board/timeline';
import {lessonModels, machineRows} from '../boards';
import {forward} from '../../math-board/algebra';

const rows = machineRows();
const c = (stage: number, phrase: string, occurrence = 0): Cue => ({beat: `machine-${String(stage).padStart(2, '0')}`, phrase, occurrence});
const m = lessonModels.example;
const positions = [270, 600, 960, 1320, 1650];
export const Machine = (props: InverseProps) => {
  const {beat} = useBeat(props, 'machine');
  const stage = beat.stage, returning = stage >= 3;
  const beats = useMemo(() => props.beats.filter((item) => item.scene === 'machine'), [props.beats]);
  const frame = useCurrentFrame(), {fps} = useVideoConfig();
  const travel = (from: Cue, to: Cue) => interpolate(frame, [cueFrame(from, beats, fps),
    cueFrame(to, beats, fps) + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ballX = stage === 0 ? positions[0] : stage === 1 ? positions[0] + travel(c(1, 'times'), c(1, 'six')) * 690 :
    stage === 2 ? positions[2] + travel(c(2, 'Six'), c(2, 'eleven')) * 690 :
    stage === 3 ? positions[4] - travel(c(3, 'subtract'), c(3, 'five')) * 690 :
    stage === 4 ? positions[2] - travel(c(4, 'divide'), c(4, 'divide by two')) * 690 : positions[0];
  const shown = (at: Cue, children: ReactNode) => <CueGroup at={at} beats={beats}>{children}</CueGroup>;
  const current = stage === 1 ? rows[0] : stage === 2 ? rows[1] : stage >= 3 && stage <= 4 ? rows[3] : stage >= 5 ? rows[4] : null;
  return <Stage title={returning ? 'Undo the last operation first.' : 'A function is a journey.'}
    chapter="02 / INTUITION" dark>
    {stage < 2 ? shown(c(0, 'function'), <Text y={330} size={64} color={colors.white} math>{m.name}</Text>) :
      <MathLine row={rows[2]} beats={beats} y={330} size={64} color={colors.white} accent={colors.mint}/>}
    {[c(0, 'multiplies'), c(1, 'six'), c(2, 'add'), c(2, 'eleven')].map((at, index) =>
      <CueGroup key={index} at={at} beats={beats}><Arrow x1={positions[index] + 95} y1={540}
        x2={positions[index + 1] - 95} y2={540} color={returning ? colors.gold : colors.mint}/></CueGroup>)}
    {shown(c(0, 'three'), <Text x={270} y={565} size={105} color={colors.mint} math>{m.input}</Text>)}
    {shown(c(0, 'multiplies'), <Text x={560} y={563} size={72} color={colors.white} math>×</Text>)}
    {shown(c(0, 'two'), <Text x={650} y={563} size={72} color={colors.white} math>{m.multiplier}</Text>)}
    {shown(c(1, 'six'), <Text x={960} y={565} size={105} color={colors.white} math>{m.multiplier * m.input}</Text>)}
    {shown(c(2, 'add'), <Text x={1280} y={563} size={72} color={colors.white} math>+</Text>)}
    {shown(c(2, 'five'), <Text x={1370} y={563} size={72} color={colors.white} math>{m.offset}</Text>)}
    {shown(c(2, 'eleven'), <Text x={1650} y={565} size={105} color={colors.gold} math>{forward(m, m.input)}</Text>)}
    {shown(c(0, 'three'), <circle cx={ballX} cy={422} r={15} fill={returning ? colors.gold : colors.mint}/>)}
    {shown(c(3, 'backwards'), <Arrow x1={1560} y1={715} x2={1055} y2={715} color={colors.gold}/>)}
    {shown(c(3, 'subtract'), <Text x={1280} y={800} size={65} color={colors.gold} math>−</Text>)}
    {shown(c(3, 'five'), <Text x={1370} y={800} size={65} color={colors.gold} math>{m.offset}</Text>)}
    {shown(c(4, 'divide'), <><Arrow x1={865} y1={715} x2={365} y2={715} color={colors.gold}/>
      <Text x={560} y={800} size={65} color={colors.gold} math>÷</Text></>)}
    {shown(c(4, 'two', 1), <Text x={650} y={800} size={65} color={colors.gold} math>{m.multiplier}</Text>)}
    {current && <MathLine row={current} beats={beats} y={905} size={62}
      color={colors.white} accent={returning ? colors.gold : colors.mint}/>}
    <Footer dark>{stage >= 7 ? 'Inverse: output → input' : 'Follow the input.'}</Footer>
  </Stage>;
};
