import type {InverseProps} from '../timeline';
import {Stage, Text, Fraction, Equation, Footer, Reveal, colors, useBeat, ease} from '../visuals';

export const Algebra = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'algebra');
  const stage = beat.stage;
  const labels = ['Name the output', 'Exchange input and output', 'Subtract 5 on both sides',
    'Cancel the fives', 'Divide both sides by 2', 'Cancel the twos', 'The reverse rule',
    'Test the rule at 11', 'Back to the beginning'];
  return <Stage title="Build the reverse rule." chapter="03 / ALGEBRA">
    <Text x={112} y={305} size={34} anchor="start" color={colors.teal}>{String(Math.min(stage + 1, 7)).padStart(2, '0')} / {labels[stage]}</Text>
    <Reveal frame={frame}>
      {stage <= 1 && <>
        <Text x={stage === 0 ? 650 : 650 + 410 * ease(frame, 40)} y={stage === 0 ? 500 : 500 - 70 * Math.sin(ease(frame, 40) * Math.PI)} size={110} color={colors.teal} math>y</Text>
        <Text x={820} y={500} size={110} math>=</Text>
        <Text x={1000} y={500} size={110} math>2</Text>
        <Text x={stage === 0 ? 1060 : 1060 - 410 * ease(frame, 40)} y={stage === 0 ? 500 : 500 + 70 * Math.sin(ease(frame, 40) * Math.PI)} size={110} color={colors.teal} math>x</Text>
        <Text x={1220} y={500} size={110} math>+</Text><Text x={1360} y={500} size={110} math>5</Text>
        {stage === 1 && <Text y={710} size={52} color={colors.teal} math>x ↔ y</Text>}
      </>}
      {stage === 2 && <><Equation>x − 5 = 2y + 5 − 5</Equation><Text y={720} size={52} color={colors.teal}>− 5 on each side</Text></>}
      {stage === 3 && <><Equation>x − 5 = 2y</Equation><Text y={720} size={52} color={colors.teal} math>5 − 5 = 0</Text></>}
      {stage === 4 && <><Fraction x={680} y={505} top="x − 5" bottom="2"/><Text x={960} y={530} size={90} math>=</Text><Fraction x={1200} y={505} top="2y" bottom="2"/></>}
      {stage === 5 && <><Text x={690} y={530} size={100} math>y =</Text><Fraction x={1080} y={505} top="x − 5" bottom="2"/></>}
      {stage === 6 && <><Text x={570} y={530} size={100} color={colors.teal} math>f⁻¹(x) =</Text><Fraction x={1200} y={505} top="x − 5" bottom="2" color={colors.teal}/></>}
      {stage === 7 && <><Text x={570} y={530} size={100} math>f⁻¹(11) =</Text><Fraction x={1200} y={505} top="11 − 5" bottom="2"/></>}
      {stage === 8 && <><Fraction x={620} y={505} top="6" bottom="2"/><Text x={1080} y={550} size={125} color={colors.teal} math>= 3</Text></>}
    </Reveal>
    <Footer>f(x) = 2x + 5</Footer>
  </Stage>;
};
