/** Authored narration anchors are separate from the reusable board and algebra logic. */
import models from './models.json';
import {cancelFactor, cancelSum, forward, spokenNumber, validateAffine, type AffineModel} from '../math-board/algebra';
import {compileBoard, type Atom, type Board, type Cue, type Fraction, type Node, type Row, type SpeechBeat} from '../math-board/timeline';

export const lessonModels = models;
const cue = (scene: string, stage: number, phrase: string, occurrence = 0): Cue => ({
  beat: `${scene}-${String(stage).padStart(2, '0')}`, phrase, occurrence,
});
const atom = (id: string, text: string | number, at?: Cue, accent = false): Atom => ({id, text: String(text), cue: at, accent});
const fraction = (id: string, top: Node[], bottom: Node[], at?: Cue): Fraction => ({id, top, bottom, cue: at});
const row = (id: string, at: Cue, nodes: Node[], label?: string): Row => ({id, cue: at, nodes, label});
const sign = (n: number) => n < 0 ? '−' : '+';

export const algebraBoard = (m: AffineModel = models.example): Board => {
  validateAffine(m);
  const a = spokenNumber(m.multiplier), b = spokenNumber(Math.abs(m.offset));
  const target = forward(m, m.input), out = spokenNumber(target), input = spokenNumber(m.input);
  const c = (stage: number, phrase: string, occurrence = 0) => cue('algebra', stage, phrase, occurrence);
  const eq = (id: string, lhs: string, variable: string, at: Cue, cues?: Cue[]) => [
    atom(id+'l', lhs, cues?.[0] ?? at, true), atom(id+'eq', '=', cues?.[1]),
    atom(id+'a', m.multiplier, cues?.[2]), atom(id+'v', variable, cues?.[3], true),
    atom(id+'sign', sign(m.offset), cues?.[4]), atom(id+'b', Math.abs(m.offset), cues?.[5]),
  ];
  const undo = (id: string, at?: Cue) => [atom(id+'s', sign(-m.offset), at), atom(id+'n', Math.abs(m.offset), at)];
  const numerator = (id: string, at?: Cue, op?: Cue, number?: Cue) => [atom(id+'x', 'x', at, true),
    atom(id+'s', sign(-m.offset), op), atom(id+'n', Math.abs(m.offset), number)];
  const balance = c(2, 'Subtract'), lhsApply = c(2, b), rhsApply = c(2, 'both sides');
  const [positive, negative] = cancelSum(atom('balanceOriginal', Math.abs(m.offset)), m.offset,
    atom('balanceAdded', Math.abs(m.offset), rhsApply), -m.offset, c(3, 'cancel'));
  const [factor, divisor] = cancelFactor(atom('divideFactor', m.multiplier),
    atom('divideDivisor', m.multiplier, c(4, a)), m.multiplier, c(5, 'cancel'));
  const balanced: Row = {...row('balance', balance, [atom('balanceX', 'x', balance, true),
    ...undo('balanceLeft', lhsApply), atom('balanceEq', '='), atom('balanceA', m.multiplier),
    atom('balanceY', 'y', undefined, true), atom('balanceSign', sign(m.offset)), positive,
    atom('balanceRightSign', sign(-m.offset), rhsApply), negative], 'Apply the same operation to both sides'),
    arrows: [{target: 'balanceLeftn', cue: lhsApply}, {target: negative.id, cue: rhsApply}]};
  return [
    row('original', c(0, 'y'), eq('original', 'y', 'x', c(0, 'y'), [c(0, 'y'), c(0, 'equals'),
      c(0, a), c(0, 'x'), c(0, 'plus'), c(0, b)]), 'Name the output'),
    row('swap', c(1, 'x equals'), eq('swap', 'x', 'y', c(1, 'x equals'), [c(1, 'x equals'), c(1, 'equals'),
      c(1, a), c(1, 'y plus'), c(1, 'plus'), c(1, b)]), 'Exchange input and output'),
    balanced,
    row('subtractResult', c(3, 'We have'), [...numerator('subResult', c(3, 'x'), c(3, 'minus', 1), c(3, b, 2)),
      atom('subResultEq', '=', c(3, 'equals')), atom('subResultA', m.multiplier, c(3, a)),
      atom('subResultY', 'y', c(3, 'y'), true)], 'The additive inverses cancel to zero'),
    {...row('divide', c(4, 'Divide'), [fraction('divideLeft', numerator('divideL'),
      [atom('divideLD', m.multiplier, c(4, a))]), atom('divideEq', '='),
      fraction('divideRight', [factor, atom('divideY', 'y', undefined, true)], [divisor])], 'Divide both sides by the same nonzero factor'),
      arrows: [{target: 'divideLD', cue: c(4, a)}, {target: divisor.id, cue: c(4, a)}]},
    row('isolate', c(5, 'So y'), [atom('isolateY', 'y', c(5, 'y'), true), atom('isolateEq', '=', c(5, 'equals')),
      fraction('isolateFraction', numerator('isolateN', c(5, 'x'), c(5, 'minus'), c(5, b)),
        [atom('isolateD', m.multiplier, c(5, a))], c(5, 'x'))], 'Isolate the original input'),
    row('rule', c(6, 'f inverse'), [atom('ruleName', `${m.name}⁻¹(x)`, c(6, 'f inverse'), true),
      atom('ruleEq', '=', c(6, 'equals')), fraction('ruleFraction', numerator('ruleN', c(6, 'quantity x'),
        c(6, 'minus'), c(6, b)), [atom('ruleD', m.multiplier, c(6, a))], c(6, 'quantity x'))], 'The reverse rule'),
    row('substitute', c(7, 'Put'), [atom('testName', `${m.name}⁻¹(${target})`, c(7, 'Put'), true),
      atom('testEq', '=', c(7, out)), fraction('testFraction', [atom('testInput', target, c(7, out+' minus')),
        atom('testMinus', sign(-m.offset), c(7, 'minus')), atom('testB', Math.abs(m.offset), c(7, b))],
      [atom('testD', m.multiplier, c(7, a))], c(7, out+' minus'))], 'Substitute the known output'),
    row('numeric', c(8, 'is '+spokenNumber(target - m.offset)), [
      fraction('numericFraction', [atom('numericN', target - m.offset)], [atom('numericD', m.multiplier)]),
      atom('numericEq', '=', c(8, 'is '+input)), atom('numericAnswer', m.input, c(8, input), true)], 'Recover the original input'),
  ];
};

export const verificationBoard = (m: AffineModel = models.example): Board => {
  validateAffine(m);
  const c = (stage: number, phrase: string) => cue('verify', stage, phrase);
  const [outer, lower] = cancelFactor(atom('verifyOuter', m.multiplier, c(2, 'Two times')),
    atom('verifyLower', m.multiplier, c(2, 'divided by two')), m.multiplier, c(2, 'cancels'));
  const [minus, plus] = cancelSum(atom('verifyMinusValue', Math.abs(m.offset), c(3, 'five')),
    -m.offset, atom('verifyPlusValue', Math.abs(m.offset), c(3, 'plus five')), m.offset, c(3, 'cancel'));
  const [plus2, minus2] = cancelSum(atom('backPlusValue', Math.abs(m.offset), c(5, 'plus five')), m.offset,
    atom('backMinusValue', Math.abs(m.offset), c(5, 'Subtract five')), -m.offset, c(6, 'cancel'));
  const [factor, denominator] = cancelFactor(atom('backFactor', m.multiplier),
    atom('backDivisor', m.multiplier), m.multiplier, c(6, 'divided by two'));
  return [
    row('verifyIdea', c(0, 'Composition'), [atom('verifyIdeaN', `${m.name}(${m.name}⁻¹(x))`)], 'Inverse → function'),
    row('verifySub', c(1, 'Replace'), [atom('verifySubN', `${m.name}(`), fraction('verifySubF',
      [atom('verifySubX', 'x'), atom('verifySubS', sign(-m.offset)), atom('verifySubB', Math.abs(m.offset))],
      [atom('verifySubD', m.multiplier)]), atom('verifySubEnd', ')')], 'Substitute the whole inverse expression'),
    row('verifyExpand', c(2, 'Two times'), [outer, atom('verifyTimes', '·'), fraction('verifyF',
      [atom('verifyX', 'x', c(2, 'x')), atom('verifySign', sign(-m.offset), c(2, 'minus')),
        atom('verifyB', Math.abs(m.offset), c(2, 'five'))], [lower]),
      atom('verifyPlus', sign(m.offset), c(2, 'plus five')), atom('verifyOffset', Math.abs(m.offset), c(2, 'plus five'))], 'Cancel a common factor'),
    row('verifySimplify', c(3, 'x minus'), [atom('verifyResultX', 'x', c(3, 'x minus'), true),
      atom('verifyMinus', sign(-m.offset), c(3, 'minus')), minus, atom('verifyPlusS', sign(m.offset), c(3, 'plus five')), plus,
      atom('verifyResultEq', '=', c(3, 'leaving')), atom('verifyResultEnd', 'x', c(3, 'leaving x'), true)], 'Additive inverses sum to zero'),
    row('backIdea', c(4, 'other direction'), [atom('backIdeaN', `${m.name}⁻¹(${m.name}(x))`)], 'Function → inverse'),
    row('backSub', c(5, 'two x'), [fraction('backFraction', [atom('backOpen', '('), atom('backA', m.multiplier),
      atom('backX', 'x', c(5, 'x')), atom('backPlus', sign(m.offset), c(5, 'plus five')), plus2,
      atom('backClose', ')'), atom('backMinus', sign(-m.offset), c(5, 'Subtract five')), minus2],
      [atom('backD', m.multiplier, c(5, 'divide by two'))])], 'Keep the substituted expression grouped'),
    row('backSimplify', c(6, 'Two x'), [fraction('backRemaining', [factor, atom('backRemainingX', 'x', undefined, true)], [denominator]),
      atom('backEq', '=', c(6, 'is x')), atom('backAnswer', 'x', c(6, 'is x'), true)], 'The nonzero common factor cancels'),
    row('verifiedBothForward', c(7, 'Both compositions'), [atom('verifiedBothForwardN', `${m.name}(${m.name}⁻¹(x)) = x`, undefined, true)], 'Inverse then function'),
    row('verifiedBothReverse', c(7, 'Both compositions'), [atom('verifiedBothReverseN', `${m.name}⁻¹(${m.name}(x)) = x`, undefined, true)], 'Function then inverse'),
  ];
};

export const practiceBoard = (m: AffineModel = models.practice): Board => {
  validateAffine(m);
  const c = (stage: number, phrase: string, occurrence = 0) => cue('practice', stage, phrase, occurrence);
  const a = spokenNumber(m.multiplier), b = spokenNumber(Math.abs(m.offset));
  const target = forward(m, m.input);
  const [old, added] = cancelSum(atom('practiceOldB', Math.abs(m.offset)), m.offset,
    atom('practiceAddedB', Math.abs(m.offset), c(3, 'both sides')), -m.offset, {...c(3, 'both sides'), edge: 'end'});
  const [factor, divisor] = cancelFactor(atom('practiceFactor', m.multiplier),
    atom('practiceDivisor', m.multiplier, c(3, a)), m.multiplier, {...c(3, a), edge: 'end'});
  return [
    row('practiceQuestion', c(0, 'three x'), [atom('practiceName', `${m.name}(x) =`), atom('practiceA', m.multiplier),
      atom('practiceX', 'x'), atom('practiceS', sign(m.offset), c(0, 'minus')),
      atom('practiceB', Math.abs(m.offset), c(0, b))], 'Find the inverse'),
    row('practicePrompt', c(0, 'inverse'), [atom('practicePromptN', `${m.name}⁻¹(x) = ?`, undefined, true)], `Check it at ${target}`),
    row('practiceOriginal', c(2, 'y equals'), [atom('practiceOriginalY', 'y'), atom('practiceOriginalEq', '=', c(2, 'equals')),
      atom('practiceOriginalA', m.multiplier, c(2, a)), atom('practiceOriginalX', 'x', c(2, 'x minus')),
      atom('practiceOriginalS', sign(m.offset), c(2, 'minus')), atom('practiceOriginalB', Math.abs(m.offset), c(2, b))], 'Start from the forward rule'),
    row('practiceSwap', c(2, 'Swap'), [atom('practiceSwapX', 'x'), atom('practiceSwapEq', '='), atom('practiceSwapA', m.multiplier),
      atom('practiceSwapY', 'y'), atom('practiceSwapS', sign(m.offset)), atom('practiceSwapB', Math.abs(m.offset))], 'Exchange input and output'),
    {...row('practiceBalance', c(3, 'Add'), [atom('practiceBalanceX', 'x'), atom('practiceLeftS', sign(-m.offset), c(3, b)),
      atom('practiceLeftB', Math.abs(m.offset), c(3, b)), atom('practiceBalanceEq', '='), atom('practiceBalanceA', m.multiplier),
      atom('practiceBalanceY', 'y'), atom('practiceOldS', sign(m.offset)), old,
      atom('practiceAddedS', sign(-m.offset), c(3, 'both sides')), added], 'Balance both sides'),
      arrows: [{target: 'practiceLeftB', cue: c(3, b)}, {target: added.id, cue: c(3, 'both sides')}]},
    row('practiceDivide', c(3, 'Then divide'), [fraction('practiceLeftF', [atom('practiceLX', 'x'), atom('practiceLS', sign(-m.offset)),
      atom('practiceLB', Math.abs(m.offset))], [atom('practiceLD', m.multiplier, c(3, a))]), atom('practiceDivideEq', '='),
      fraction('practiceRightF', [factor, atom('practiceRightY', 'y')], [divisor])], 'Divide by the same nonzero factor'),
    row('practiceInverse', c(4, 'g inverse'), [atom('practiceInverseName', `${m.name}⁻¹(x)`, undefined, true),
      atom('practiceInverseEq', '=', c(4, 'equals')), fraction('practiceInverseF', [atom('practiceInverseX', 'x', c(4, 'x plus')),
        atom('practiceInverseS', sign(-m.offset), c(4, 'plus')), atom('practiceInverseB', Math.abs(m.offset), c(4, b))],
      [atom('practiceInverseD', m.multiplier, c(4, a))], c(4, 'x plus'))], 'Name the reverse rule'),
    row('practiceTest', c(5, 'At eight'), [atom('practiceTestName', `${m.name}⁻¹(${target}) =`), fraction('practiceTestF',
      [atom('practiceTestN', target, c(5, 'eight plus')), atom('practiceTestS', sign(-m.offset), c(5, 'plus')),
        atom('practiceTestB', Math.abs(m.offset), c(5, b))], [atom('practiceTestD', m.multiplier, c(5, a))])], 'Substitute the output'),
    row('practiceCompute', c(5, 'Twelve'), [fraction('practiceComputeF', [atom('practiceComputeN', target - m.offset)],
      [atom('practiceComputeD', m.multiplier)]), atom('practiceComputeEq', '=', c(5, 'is four')),
      atom('practiceAnswer', m.input, c(5, 'is four'), true)], 'Recover the input'),
    row('practiceForward', c(6, 'g of four'), [atom('practiceForwardName', `${m.name}(${m.input}) =`),
      atom('practiceForwardA', m.multiplier, c(6, a)), atom('practiceForwardTimes', '·', c(6, 'times')),
      atom('practiceForwardInput', m.input, c(6, 'times four')), atom('practiceForwardS', sign(m.offset), c(6, 'minus')),
      atom('practiceForwardB', Math.abs(m.offset), c(6, 'minus four'))], 'Verify forwards'),
    row('practiceCheck', c(6, 'Twelve'), [atom('practiceProduct', m.multiplier * m.input), atom('practiceCheckS', sign(m.offset), c(6, 'minus four', 1)),
      atom('practiceCheckB', Math.abs(m.offset), c(6, 'minus four', 1)), atom('practiceCheckEq', '=', c(6, 'is eight')),
      atom('practiceCheckOut', target, c(6, 'is eight'), true)], 'The forward rule returns the output'),
  ];
};

/** Check all authored cues before the renderer starts producing frames. */
export const validateMathBoards = (beats: readonly SpeechBeat[], fps: number): void => {
  for (const board of [algebraBoard(), verificationBoard(), practiceBoard(), machineRows(), notationRows()]) compileBoard(board, beats, fps);
};

export const machineRows = (m: AffineModel = models.example): Board => {
  const c = (stage: number, phrase: string, occurrence = 0) => cue('machine', stage, phrase, occurrence);
  const a = spokenNumber(m.multiplier), b = spokenNumber(Math.abs(m.offset));
  const input = spokenNumber(m.input), middle = m.multiplier * m.input, middleWord = spokenNumber(middle);
  const output = forward(m, m.input), outputWord = spokenNumber(output);
  return [
    row('journeyMultiply', c(1, input), [atom('journeyInput', m.input), atom('journeyTimes', '×', c(1, 'times')),
      atom('journeyFactor', m.multiplier, c(1, a)), atom('journeyEq', '=', c(1, 'is')), atom('journeyProduct', middle, c(1, middleWord), true)]),
    row('journeyAdd', c(2, middleWord), [atom('journeyMiddle', middle), atom('journeyPlus', sign(m.offset), c(2, 'plus')),
      atom('journeyOffset', Math.abs(m.offset), c(2, b, 1)), atom('journeyAddEq', '=', c(2, 'is')), atom('journeyOutput', output, c(2, outputWord), true)]),
    row('journeyRule', c(2, 'f of x'), [atom('journeyName', `${m.name}(x)`), atom('journeyRuleEq', '=', c(2, 'equals')),
      atom('journeyA', m.multiplier, c(2, a)), atom('journeyX', 'x', c(2, 'x plus')),
      atom('journeyS', sign(m.offset), c(2, 'plus five', 1)), atom('journeyB', Math.abs(m.offset), c(2, b, 2))]),
    row('journeySubtract', c(3, outputWord), [atom('journeyReverseInput', output), atom('journeyMinus', sign(-m.offset), c(3, 'subtract')),
      atom('journeyReverseOffset', Math.abs(m.offset), c(3, b)), atom('journeyReverseEq', '=', c(4, 'is')),
      atom('journeyDifference', middle, c(4, middleWord), true)]),
    row('journeyDivide', c(5, middleWord), [atom('journeyDividend', middle), atom('journeyDivideSign', '÷', c(5, 'divided')),
      atom('journeyDivisor', m.multiplier, c(5, a)), atom('journeyDivideEq', '=', c(5, 'is')),
      atom('journeyRecovered', m.input, c(5, input), true)]),
  ];
};

export const notationRows = (m: AffineModel = models.example): Board => {
  const c = (stage: number, phrase: string, occurrence = 0) => cue('notation', stage, phrase, occurrence);
  const output = forward(m, m.input), reciprocalOutput = forward(m, output);
  return [
    row('inverseValue', c(1, 'At eleven'), [atom('inverseValueName', `${m.name}⁻¹(${output})`),
      atom('inverseValueEq', '=', c(1, 'returns')), atom('inverseValueResult', m.input, c(1, spokenNumber(m.input)), true)]),
    row('reciprocalWork', c(2, 'Since'), [atom('reciprocalWorkName', `${m.name}(${output}) =`),
      atom('reciprocalWorkFactor', m.multiplier, c(2, 'two')), atom('reciprocalWorkTimes', '·', c(2, 'times')),
      atom('reciprocalWorkInput', output, c(2, 'eleven', 1)), atom('reciprocalWorkPlus', sign(m.offset), c(2, 'plus')),
      atom('reciprocalWorkOffset', Math.abs(m.offset), c(2, 'five')), atom('reciprocalWorkEq', '=', c(2, 'is')),
      atom('reciprocalWorkOutput', reciprocalOutput, c(2, spokenNumber(reciprocalOutput)), true)]),
    row('reciprocalValue', c(2, 'this is'), [atom('reciprocalName', `1 / ${m.name}(${output}) =`),
      atom('reciprocalOne', '1', c(2, 'one over')), atom('reciprocalBar', '/', c(2, 'over')),
      atom('reciprocalDenominator', reciprocalOutput, c(2, spokenNumber(reciprocalOutput), 1), true)]),
  ];
};
