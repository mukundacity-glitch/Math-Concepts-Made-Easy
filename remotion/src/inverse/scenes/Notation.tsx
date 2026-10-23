import {useMemo} from 'react';
import type {InverseProps} from '../timeline';
import {Stage, Text, Fraction, Footer, colors, useBeat} from '../visuals';
import {MathLine} from '../../math-board/MathBoard';
import {notationRows} from '../boards';

const rows = notationRows();
export const Notation = (props: InverseProps) => {
  const {beat} = useBeat(props, 'notation');
  const beats = useMemo(() => props.beats.filter((item) => item.scene === 'notation'), [props.beats]);
  return <Stage title="Inverse ≠ reciprocal." chapter="07 / THE NOTATION">
    <Text x={540} y={390} size={38} color={colors.teal}>REVERSE THE MAPPING</Text>
    <Text x={1380} y={390} size={38} color={colors.coral}>DIVIDE ONE BY THE OUTPUT</Text>
    <line x1={960} x2={960} y1={430} y2={820} stroke="#D1CDC2" strokeWidth={2}/>
    <Text x={540} y={570} size={100} color={colors.teal} math>f⁻¹(x)</Text>
    <Fraction x={1380} y={535} top="1" bottom="f(x)" size={80}/>
    <MathLine row={rows[0]} beats={beats} x={540} y={790} size={78} color={colors.teal}/>
    <MathLine row={rows[1]} beats={beats} x={1380} y={730} size={50}/>
    <MathLine row={rows[2]} beats={beats} x={1380} y={825} size={56} color={colors.coral}/>
    <Footer>{beat.stage < 3 ? 'The superscript −1 names an inverse function.' : '3 ≠ 1 / 27'}</Footer>
  </Stage>;
};
