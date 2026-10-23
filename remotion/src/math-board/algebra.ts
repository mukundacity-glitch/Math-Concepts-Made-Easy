import type {Atom, Cue} from './timeline';

export type AffineModel = {readonly name: string; readonly multiplier: number;
  readonly offset: number; readonly input: number};
export const validateAffine = (model: AffineModel) => {
  if (!/^[a-z]$/i.test(model.name) || ![model.multiplier, model.offset, model.input].every(Number.isFinite) ||
    model.multiplier === 0) throw new Error('An affine inverse requires a finite nonzero multiplier');
};
export const forward = (model: AffineModel, x: number) => model.multiplier * x + model.offset;
export const inverse = (model: AffineModel, x: number) => (x - model.offset) / model.multiplier;

/** Mark only a verified additive-inverse pair, never a same-looking term on the other side. */
export const cancelSum = (a: Atom, aValue: number, b: Atom, bValue: number, cue: Cue): [Atom, Atom] => {
  if (![aValue, bValue].every(Number.isFinite) || aValue + bValue !== 0 || aValue === 0 ||
    Number(a.text) !== Math.abs(aValue) || Number(b.text) !== Math.abs(bValue)) {
    throw new Error('Only nonzero additive inverses can cancel to zero');
  }
  return [{...a, cancel: cue}, {...b, cancel: cue}];
};
/** Division cancels a nonzero common factor, not an addend inside a sum. */
export const cancelFactor = (numeratorFactor: Atom, denominator: Atom, value: number, cue: Cue): [Atom, Atom] => {
  if (!Number.isFinite(value) || value === 0 || Number(numeratorFactor.text) !== value ||
    Number(denominator.text) !== value) throw new Error('Cancellation requires the same nonzero factor');
  return [{...numeratorFactor, cancel: cue}, {...denominator, cancel: cue}];
};

// Only speech anchors use this vocabulary. Displayed mathematics uses the model's values.
export const spokenNumber = (value: number): string => {
  const small = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
    'seventeen', 'eighteen', 'nineteen'];
  if (Number.isInteger(value) && value < 0) return 'negative ' + spokenNumber(-value);
  if (Number.isInteger(value) && value >= 0 && value < 20) return small[value];
  if (Number.isInteger(value) && value >= 20 && value < 100) return (
    ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'][Math.floor(value / 10)] +
    (value % 10 ? '-' + small[value % 10] : ''));
  throw new Error('Supply an authored speech anchor for this number: ' + value);
};
