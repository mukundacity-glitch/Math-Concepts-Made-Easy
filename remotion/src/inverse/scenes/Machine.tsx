import type {InverseProps} from '../timeline';
import {Stage, Text, Arrow, colors, useBeat, ease, Footer, Reveal} from '../visuals';

export const Machine = (props: InverseProps) => {
  const {beat, frame} = useBeat(props, 'machine');
  const stage = beat.stage;
  const returning = stage >= 3;
  const progress = ease(frame, 55);
  const positions = [270, 600, 960, 1320, 1650];
  const ballX = stage === 0 ? 270 : stage === 1 ? 270 + progress * 690 : stage === 2 ? 960 + progress * 690 :
    stage === 3 ? 1650 - progress * 690 : stage === 4 ? 960 - progress * 690 : 270;
  return <Stage title={returning ? 'Undo the last operation first.' : 'A function is a journey.'}
    chapter="02 / INTUITION" dark>
    <Text y={330} size={64} color={colors.white} math>{stage >= 2 ? 'f(x) = 2x + 5' : 'f'}</Text>
    {[0, 1, 2, 3].map((index) => <Arrow key={index} x1={positions[index] + 95} y1={540}
      x2={positions[index + 1] - 95} y2={540} color={returning ? colors.gold : colors.mint}/>)}
    <Text x={270} y={565} size={105} color={colors.mint} math>3</Text>
    <Text x={600} y={563} size={72} color={colors.white} math>× 2</Text>
    <Text x={960} y={565} size={105} color={colors.white} math>{stage >= 1 ? '6' : ''}</Text>
    <Text x={1320} y={563} size={72} color={colors.white} math>+ 5</Text>
    <Text x={1650} y={565} size={105} color={colors.gold} math>{stage >= 2 ? '11' : ''}</Text>
    <circle cx={ballX} cy={422} r={15} fill={returning ? colors.gold : colors.mint}/>
    {returning && <Reveal frame={frame}>
      <Arrow x1={1560} y1={715} x2={1055} y2={715} color={colors.gold}/>
      <Text x={1320} y={800} size={65} color={colors.gold} math>− 5</Text>
      {stage >= 4 && <><Arrow x1={865} y1={715} x2={365} y2={715} color={colors.gold}/>
        <Text x={600} y={800} size={65} color={colors.gold} math>÷ 2</Text></>}
    </Reveal>}
    <Text y={905} size={62} color={returning ? colors.gold : colors.mint} math>{stage === 1 ? '3 × 2 = 6' : stage === 2 ? '6 + 5 = 11' : stage === 3 ? '11 − 5' : stage === 4 ? '11 − 5 = 6' : stage >= 5 ? '6 ÷ 2 = 3' : ''}</Text>
    <Footer dark>{stage < 3 ? 'Multiply, then add.' : stage < 7 ? 'Subtract, then divide.' : 'Inverse: output → input'}</Footer>
  </Stage>;
};
