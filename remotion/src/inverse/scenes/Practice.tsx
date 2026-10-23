import type {InverseProps} from '../timeline';
import {Stage, Text, Equation, Footer, colors, useBeat, Reveal} from '../visuals';

export const Practice = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'practice');
  const stage = beat.stage;
  return <Stage title={stage < 2 ? 'Find the way back.' : 'Let us work it through.'} chapter="08 / YOUR TURN">
    <Text y={330} size={58} color={colors.teal} math>g(x) = 3x − 4</Text>
    <Reveal frame={frame}>
      {stage === 0 && <><Equation y={550}>g⁻¹(x) = ?</Equation><Text y={745} size={60} math>g⁻¹(8) = ?</Text></>}
      {stage === 1 && <><Equation y={550}>g⁻¹(x) = ?</Equation><Text y={745} size={52} color={colors.teal}>Pause. Sketch the reverse journey.</Text></>}
      {stage === 2 && <><Equation y={510}>y = 3x − 4</Equation><Equation y={710} color={colors.teal}>x = 3y − 4</Equation></>}
      {stage === 3 && <><Equation y={510}>x + 4 = 3y</Equation><Equation y={710} color={colors.teal}>y = (x + 4) / 3</Equation></>}
      {stage === 4 && <Equation y={570} color={colors.teal}>g⁻¹(x) = (x + 4) / 3</Equation>}
      {stage === 5 && <><Equation y={480} size={84}>g⁻¹(8) = (8 + 4) / 3</Equation>
        <Equation y={710} color={colors.teal}>= 12 / 3 = 4</Equation></>}
      {stage === 6 && <><Equation y={480} size={84}>g(4) = 3 · 4 − 4</Equation>
        <Equation y={710} color={colors.teal}>= 12 − 4 = 8</Equation></>}
    </Reveal>
    <Footer>{stage < 2 ? 'Undo subtraction first.' : 'Add 4, then divide by 3.'}</Footer>
  </Stage>;
};
