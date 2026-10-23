import type {InverseProps} from '../timeline';
import {Stage, Text, Fraction, Footer, colors, useBeat, Reveal} from '../visuals';

export const Notation = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'notation');
  const stage = beat.stage;
  return <Stage title="Inverse ≠ reciprocal." chapter="07 / THE NOTATION">
    <Text x={540} y={390} size={38} color={colors.teal}>REVERSE THE MAPPING</Text>
    <Text x={1380} y={390} size={38} color={colors.coral}>DIVIDE ONE BY THE OUTPUT</Text>
    <line x1={960} x2={960} y1={430} y2={820} stroke="#D1CDC2" strokeWidth={2}/>
    <Text x={540} y={570} size={100} color={colors.teal} math>f⁻¹(x)</Text>
    <Fraction x={1380} y={535} top="1" bottom="f(x)" size={80}/>
    {stage >= 1 && <Reveal frame={frame}><Text x={540} y={790} size={78} color={colors.teal} math>f⁻¹(11) = 3</Text></Reveal>}
    {stage >= 2 && <><Text x={1380} y={730} size={50} math>f(11) = 2 · 11 + 5 = 27</Text>
      <Text x={1380} y={825} size={66} color={colors.coral} math>1 / f(11) = 1 / 27</Text></>}
    <Footer>{stage < 3 ? 'The superscript −1 names an inverse function.' : '3 ≠ 1 / 27'}</Footer>
  </Stage>;
};
