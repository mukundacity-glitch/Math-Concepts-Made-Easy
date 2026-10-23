import {useMemo} from 'react';
import {CueGroup} from '../../math-board/MathBoard';
import type {Cue} from '../../math-board/timeline';
import type {InverseProps} from '../timeline';
import {Stage, Text, Footer, Arrow, colors, useBeat, Reveal} from '../visuals';

export const Domain = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'domain');
  const stage = beat.stage;
  const beats = useMemo(() => props.beats.filter((item) => item.scene === 'domain'), [props.beats]);
  const c = (stage: number, phrase: string): Cue => ({beat: `domain-${String(stage).padStart(2, '0')}`, phrase});
  const restricted = stage >= 5;
  const reverse = stage === 2;
  const curve = Array.from({length: 121}, (_, index) => {
    const input = restricted ? index / 40 : -3 + index / 20;
    return `${index === 0 ? 'M' : 'L'} ${1390 + input * 70} ${890 - input * input * 70}`;
  }).join(' ');
  return <Stage title={restricted ? 'Choose a domain with one way back.' : 'Not every function can be undone.'}
    chapter="06 / EXISTENCE">
    <Text x={112} y={340} size={68} color={colors.teal} anchor="start" math>f(x) = x²</Text>
    {stage < 5 ? <>
      <CueGroup at={c(1, 'Two squared')} beats={beats}><Text x={230} y={485} size={82} math>2</Text></CueGroup>
      <CueGroup at={c(1, 'negative two')} beats={beats}><Text x={230} y={710} size={82} math>−2</Text></CueGroup>
      {stage >= 1 && <>
        <CueGroup at={c(1, 'four')} beats={beats}><Arrow x1={reverse ? 700 : 340} y1={reverse ? 565 : 460} x2={reverse ? 340 : 700} y2={reverse ? 460 : 565}/></CueGroup>
        <CueGroup at={c(1, 'negative two')} beats={beats}><Arrow x1={reverse ? 700 : 340} y1={reverse ? 605 : 685} x2={reverse ? 340 : 700} y2={reverse ? 685 : 605}/></CueGroup>
        <CueGroup at={c(1, 'four')} beats={beats}><Text x={800} y={610} size={100} math>4</Text></CueGroup>
        <CueGroup at={c(1, 'also four')} beats={beats}><Text x={520} y={820} size={48} color={stage === 2 ? colors.coral : colors.teal}>
          {stage === 2 ? 'Two outputs: not a function' : 'Two inputs. One output.'}
        </Text></CueGroup>
      </>}
    </> : <Reveal frame={frame}>
      <CueGroup at={c(5, 'x greater')} beats={beats}><Text x={112} y={480} size={86} color={colors.teal} anchor="start" math>x ≥ 0</Text></CueGroup>
      {stage >= 6 && <><CueGroup at={c(6, 'square root')} beats={beats}><Text x={112} y={620} size={80} anchor="start" math>f⁻¹(x) = √x</Text></CueGroup>
        <CueGroup at={c(6, 'Four returns')} beats={beats}><Text x={112} y={740} size={70} color={colors.teal} anchor="start" math>4 → 2</Text></CueGroup></>}
    </Reveal>}
    <Arrow x1={1135} y1={890} x2={1650} y2={890}/>
    <Arrow x1={1390} y1={925} x2={1390} y2={245}/>
    <Text x={1680} y={905} size={34} math>x</Text><Text x={1390} y={230} size={34} math>y</Text>
    <path d={curve} fill="none" stroke={colors.teal} strokeWidth={5}/>
    {stage >= 3 && stage < 5 && <><line x1={1135} x2={1650} y1={610} y2={610}
      stroke={colors.coral} strokeWidth={4} strokeDasharray="10 10"/>
      <circle cx={1250} cy={610} r={10} fill={colors.coral}/><circle cx={1530} cy={610} r={10} fill={colors.coral}/>
      <Text x={1690} y={620} size={34} color={colors.coral} math>y = 4</Text></>}
    <Footer>{stage === 7 ? '√(x²) = |x|;  |x| = x when x ≥ 0' : stage === 4 ? 'One-to-one: each output has at most one input.' :
      stage >= 6 ? 'Inverse domain: [0, ∞)   /   range: [0, ∞)' : 'The horizontal line test'}</Footer>
  </Stage>;
};
