import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

const cache = new Map();
function load(filename) {
  const full = path.resolve(filename);
  if (cache.has(full)) return cache.get(full);
  if (full.endsWith('.json')) return JSON.parse(fs.readFileSync(full, 'utf8'));
  const module = {exports: {}};
  const code = ts.transpileModule(fs.readFileSync(full, 'utf8'), {compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  }}).outputText;
  new Function('require', 'module', 'exports', code)((name) => load(path.resolve(path.dirname(full), name + (name.endsWith('.json') ? '' : '.ts'))), module, module.exports);
  cache.set(full, module.exports);
  return module.exports;
}
const timeline = load('src/math-board/timeline.ts');
const algebra = load('src/math-board/algebra.ts');
const boards = load('src/inverse/boards.ts');
const story = JSON.parse(fs.readFileSync('src/inverse/storyboard.json', 'utf8'));
const preview = story.beats.map((beat) => ({...beat,
  durationInFrames: Math.ceil((beat.speech.split(/\s+/).length / 2.35 + beat.holdSeconds) * 30)}));

for (const [scene, build] of [['algebra', boards.algebraBoard], ['verify', boards.verificationBoard], ['practice', boards.practiceBoard], ['machine', boards.machineRows], ['notation', boards.notationRows]]) {
  test(`${scene}: every reveal, arrow and cancellation matches an authored spoken phrase`, () => {
    const beats = preview.filter((beat) => beat.scene === scene);
    const board = build();
    const compiled = timeline.compileBoard(board, beats, 30);
    assert.ok(compiled.frames.size > board.length);
    assert.ok(compiled.cancellations.size >= (['algebra', 'verify', 'practice'].includes(scene) ? 4 : 0));
    const duration = beats.reduce((sum, beat) => sum + beat.durationInFrames, 0);
    assert.ok([...compiled.frames.values(), ...compiled.cancellations.values()].every((frame) => frame < duration));
  });
}

test('opening equation and final answer wait for their spoken numbers', () => {
  const plan = timeline.compileBoard(boards.algebraBoard(), preview.filter((beat) => beat.scene === 'algebra'), 30);
  assert.ok(plan.frames.get('originalb') > plan.frames.get('originala'));
  assert.ok(plan.frames.get('originala') > plan.frames.get('originaleq'));
  assert.ok(plan.cancellations.get('balanceOriginal') > plan.frames.get('balanceAdded'));
  assert.ok(plan.frames.get('numericAnswer') > plan.frames.get('numericN'));
  assert.equal(plan.cancellations.has('balanceLeftn'), false);
  assert.equal(plan.cancellations.has('balanceOriginal'), true);
  assert.equal(plan.cancellations.has('balanceAdded'), true);
});

test('real timestamps replace estimates; missing words and premature cancellation fail', () => {
  const beats = [{id: 'b', speech: 'Subtract seven', audioSrc: 'voice.wav', durationInFrames: 180,
    words: [{text: 'Subtract', start: .4, end: .8}, {text: 'seven', start: 2, end: 2.4}]}];
  const cue = {beat: 'b', phrase: 'seven'};
  assert.equal(timeline.cueFrame(cue, beats, 30), 60);
  assert.throws(() => timeline.cueFrame(cue, [{...beats[0], words: undefined}], 30), /real word/);
  assert.throws(() => timeline.cueFrame({...cue, phrase: 'five'}, beats, 30), /absent/);
  assert.throws(() => timeline.compileBoard([{id: 'r', cue, nodes: [{id: 'n', text: '7',
    cancel: {...cue, phrase: 'Subtract'}}]}], beats, 30), /unseen/);
});

test('affine calculations and cancellation logic accept different coefficients and signs', () => {
  for (const model of [{name: 'h', multiplier: 7, offset: 9, input: 6},
    {name: 'p', multiplier: -3, offset: -8, input: 2}]) {
    for (const x of [-100, -.5, 0, 9, 100]) {
      assert.ok(Math.abs(algebra.inverse(model, algebra.forward(model, x)) - x) < 1e-10);
      assert.ok(Math.abs(algebra.forward(model, algebra.inverse(model, x)) - x) < 1e-10);
    }
    const nodes = boards.algebraBoard(model).flatMap((row) => timeline.walkNodes(row.nodes));
    assert.equal(nodes.find((node) => node.id === 'originala').text, String(model.multiplier));
    assert.equal(nodes.find((node) => node.id === 'balanceAdded').text, String(Math.abs(model.offset)));
    assert.equal(nodes.find((node) => node.id === 'testInput').text, String(algebra.forward(model, model.input)));
  }
  assert.throws(() => algebra.validateAffine({name: 'q', multiplier: 0, offset: 7, input: 2}), /nonzero/);
  const a = {id: 'a', text: '7'}, b = {id: 'b', text: '3'}, cue = {beat: 'b', phrase: 'cancel'};
  assert.throws(() => algebra.cancelSum(a, 7, b, -3, cue), /additive inverses/);
  assert.throws(() => algebra.cancelFactor(a, b, 7, cue), /same nonzero/);
});

// Export this tiny TS loader for local QA scripts, without depending on a TS runtime.
export {load};

const masterProps = 'build/inverse/lesson.json';
test('local generated narration: every board cue resolves to a real word boundary', {skip: !fs.existsSync(masterProps)}, () => {
  const props = JSON.parse(fs.readFileSync(masterProps, 'utf8'));
  for (const [scene, build] of [['algebra', boards.algebraBoard], ['verify', boards.verificationBoard], ['practice', boards.practiceBoard], ['machine', boards.machineRows], ['notation', boards.notationRows]]) {
    const plan = timeline.compileBoard(build(), props.beats.filter((beat) => beat.scene === scene), 30);
    assert.ok(plan.frames.size > 0);
  }
});


test('diagram calculations wait for each operation and result', () => {
  const journey = timeline.compileBoard(boards.machineRows(), preview.filter(b => b.scene === 'machine'), 30);
  assert.ok(journey.frames.get('journeyPlus') > journey.frames.get('journeyProduct'));
  assert.ok(journey.frames.get('journeyOutput') > journey.frames.get('journeyOffset'));
  assert.ok(journey.frames.get('journeyRecovered') > journey.frames.get('journeyDivisor'));
  const notation = timeline.compileBoard(boards.notationRows(), preview.filter(b => b.scene === 'notation'), 30);
  assert.ok(notation.frames.get('reciprocalWorkOutput') > notation.frames.get('reciprocalWorkOffset'));
  assert.ok(notation.frames.get('reciprocalDenominator') > notation.frames.get('reciprocalWorkOutput'));
});
