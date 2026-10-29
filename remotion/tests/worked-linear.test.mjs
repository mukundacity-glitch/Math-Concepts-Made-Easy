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
const cinematic = load('src/cinematic/timeline.ts');
const props = JSON.parse(fs.readFileSync('src/cinematic/elimination-preview.json', 'utf8'));
const {board, beats, boardStates} = props.chapters[0];
const plan = timeline.compileBoard(board, beats, 30);
const start = (id) => beats.slice(0, beats.findIndex((b) => b.id === id)).reduce((sum, b) => sum + b.durationInFrames, 0);

test('elimination uses the existing cinematic validator and frame clock', () => {
  assert.equal(cinematic.cinematicFrames(props), beats.reduce((sum,b) => sum+b.durationInFrames, 0));
  assert.equal(props.previewMode, true);
  for (const beat of beats) assert.ok(beat.teaching.reason && beat.teaching.operation);
});

test('paired terms highlight before cancellation and originals reset afterward', () => {
  for (const id of ['first-plus-y', 'second-minus-y']) {
    assert.equal(plan.highlights.get(id)[0], start('method'));
    assert.ok(plan.highlights.get(id)[1] < plan.cancellations.get(id));
    assert.equal(plan.cancellationEnds.get(id), start('divide'));
  }
  assert.equal(plan.cancellations.get('first-plus-y'), plan.cancellations.get('second-minus-y'));
});

test('retention pins originals and keeps the exact needed intermediate steps', () => {
  for (const state of boardStates.slice(1)) {
    const rows = timeline.retainedRows(board, boardStates, beats, 30, timeline.cueFrame(state.cue, beats, 30));
    assert.deepEqual(rows.map((r) => r.id), state.rowIds);
    assert.ok(rows.some((r) => r.id === 'first') && rows.some((r) => r.id === 'second'));
    assert.ok(rows.length <= 4);
  }
  assert.deepEqual(timeline.retainedRows(board, boardStates, beats, 30, start('substitute')).map((r) => r.id),
    ['first', 'second', 'solve-x', 'substitute']);
});

test('practice hold precedes both answers and final checks remain visible', () => {
  const pause = beats.find((b) => b.id === 'pause');
  const wordsSeconds = pause.speech.split(/\s+/).length / 2.2;
  assert.ok(pause.durationInFrames >= Math.ceil((wordsSeconds + 6) * 30));
  assert.ok(plan.frames.get('check-first') >= start('check-first'));
  assert.ok(plan.frames.get('check-second') >= start('check-second'));
  assert.deepEqual(timeline.retainedRows(board, boardStates, beats, 30, start('interpret')).map((r) => r.id),
    ['first', 'second', 'check-first', 'check-second']);
});

test('missing cues, invalid retention and partial timing fail closed', () => {
  const broken = structuredClone(board);
  broken[0].nodes[0].cue.phrase = 'this phrase is absent';
  assert.throws(() => timeline.compileBoard(broken, beats, 30), /absent/);
  assert.throws(() => timeline.retainedRows(board, [{...boardStates[0], rowIds: ['missing']}], beats, 30, 0), /retained/);
  const audio = beats.map((b) => ({...b, audioSrc: 'cinematic/day-001/worked-example/' + b.id + '.wav', audioSha256: 'a'.repeat(64)}));
  assert.throws(() => cinematic.cinematicFrames({...props, chapters: [{...props.chapters[0], beats: audio}]}), /narration/);
});

test('real word boundaries drive both display and retention cues', () => {
  const real = [{id: 'real', speech: 'Now x', durationInFrames: 150, audioSrc: 'voice.wav',
    words: [{text: 'Now', start: .5, end: .8}, {text: 'x', start: 2, end: 2.4}]}];
  const cue = {beat: 'real', phrase: 'x'};
  const rows = [{id: 'r', cue, nodes: [{id: 'x', text: 'x'}]}];
  assert.equal(timeline.compileBoard(rows, real, 30).frames.get('x'), 60);
  assert.deepEqual(timeline.retainedRows(rows, [{cue, rowIds: ['r'], reason: 'test'}], real, 30, 59), []);
  assert.equal(timeline.retainedRows(rows, [{cue, rowIds: ['r'], reason: 'test'}], real, 30, 60)[0].id, 'r');
});
