import type {InverseProps} from '../timeline';
import {Stage, Text, Arrow, Equation, Footer, colors, useBeat, Reveal} from '../visuals';

export const Recap = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'recap');
  const stage = beat.stage;
  return <Stage title="An inverse is the way back." chapter="09 / KEEP THE IDEA" dark>
    <Reveal frame={frame}>
      {stage === 0 || stage === 4 ? <>
        <Text x={500} y={570} size={180} color={colors.mint} math>3</Text>
        <Text x={1420} y={570} size={180} color={colors.gold} math>11</Text>
        <Arrow x1={680} y1={420} x2={1240} y2={420} color={colors.mint}/>
        <Arrow x1={1240} y1={700} x2={680} y2={700} color={colors.gold}/>
        <Text y={370} size={52} color={colors.mint} math>f</Text>
        <Text y={800} size={52} color={colors.gold} math>f⁻¹</Text>
      </> : stage === 1 ? <><Equation color={colors.white} size={90}>x ↔ y</Equation>
        <Equation y={680} color={colors.mint} size={80}>f(f⁻¹(x)) = f⁻¹(f(x)) = x</Equation></> : stage === 2 ? <>
        <Equation color={colors.white}>(a, b) ↔ (b, a)</Equation><Equation y={690} color={colors.gold}>y = x</Equation>
      </> : <><Equation color={colors.mint}>One-to-one</Equation>
        <Text y={690} size={52} color={colors.white}>Choose the domain before reversing.</Text></>}
    </Reveal>
    <Footer dark>{stage === 4 ? 'MATH CONCEPTS MADE EASY' : 'Reverse. Solve. Verify.'}</Footer>
  </Stage>;
};
