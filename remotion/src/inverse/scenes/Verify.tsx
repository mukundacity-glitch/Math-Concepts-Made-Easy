import type {InverseProps} from '../timeline';
import {Stage, Text, Fraction, Equation, Footer, Reveal, colors, useBeat} from '../visuals';

export const Verify = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'verify');
  const stage = beat.stage;
  return <Stage title="A round trip returns the input." chapter="04 / VERIFY">
    <Text y={320} size={44} color={colors.teal}>{stage < 4 ? 'INVERSE → FUNCTION' : 'FUNCTION → INVERSE'}</Text>
    <Reveal frame={frame}>
      {stage === 0 && <Equation>f(f⁻¹(x))</Equation>}
      {stage === 1 && <><Text x={470} y={535} size={92} math>f(f⁻¹(x)) = f(</Text><Fraction x={1190} y={505} top="x − 5" bottom="2"/><Text x={1430} y={535} size={92} math>)</Text></>}
      {stage === 2 && <><Text x={550} y={540} size={108} math>2 ·</Text><Fraction x={960} y={505} top="x − 5" bottom="2"/><Text x={1370} y={540} size={108} math>+ 5</Text></>}
      {stage === 3 && <><Equation>x − 5 + 5 = x</Equation><Text y={730} size={60} color={colors.teal} math>− 5 + 5 = 0</Text></>}
      {stage === 4 && <Equation>f⁻¹(f(x))</Equation>}
      {stage === 5 && <Fraction y={505} top="(2x + 5) − 5" bottom="2" size={100}/>}
      {stage === 6 && <><Fraction x={650} y={505} top="2x" bottom="2"/><Text x={1100} y={540} size={110} color={colors.teal} math>= x</Text></>}
      {stage === 7 && <><Equation color={colors.teal} size={88}>f(f⁻¹(x)) = x</Equation><Equation y={690} color={colors.teal} size={88}>f⁻¹(f(x)) = x</Equation></>}
    </Reveal>
    <Footer>{stage === 7 ? 'Both domains and ranges: ℝ' : 'Substitute the whole expression. Then simplify.'}</Footer>
  </Stage>;
};
