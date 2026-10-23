import type {InverseProps} from '../timeline';
import {Stage, Text, Arrow, Reveal, colors, useBeat, ease} from '../visuals';

export const Opening = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'opening');
  const stage = beat.stage;
  return <Stage title={stage < 2 ? 'Can we find the way back?' : 'Inverse functions'} chapter="01 / THE QUESTION" dark>
    {stage < 2 ? <>
      <Text x={450} y={555} size={180} color={colors.mint} math>3</Text>
      <Arrow x1={600} y1={500} x2={1250} y2={500} color={colors.muted} progress={ease(frame, 30)}/>
      <Text x={1440} y={555} size={180} color={colors.gold} math>11</Text>
      <Text y={410} size={48} color={colors.white}>f</Text>
      <Reveal frame={frame}><Text y={770} size={150} color={colors.gold}>?</Text></Reveal>
    </> : <Reveal frame={frame}>
      <Text x={112} y={515} size={150} color={colors.white} anchor="start" math>f⁻¹</Text>
      <Text x={590} y={492} size={76} color={colors.mint} anchor="start">The mathematics</Text>
      <Text x={590} y={590} size={76} color={colors.mint} anchor="start">of coming back.</Text>
      <Text x={590} y={780} size={42} color={colors.white} anchor="start">
        {stage === 2 ? 'FUNCTIONS  /  LESSON 43' : 'Find it. Verify it. Know when it exists.'}
      </Text>
    </Reveal>}
  </Stage>;
};
