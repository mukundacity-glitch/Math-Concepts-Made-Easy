import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

const story = JSON.parse(fs.readFileSync('src/inverse/storyboard.json', 'utf8'));
const source = fs.readFileSync('src/inverse/timeline.ts', 'utf8');
const compiled = ts.transpileModule(source, {compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true,
}}).outputText;
const module = {exports: {}};
new Function('require', 'exports', 'module', compiled)(
  (name) => { assert.equal(name, './storyboard.json'); return story; }, module.exports, module);
const {previewBeats, totalFrames, validateBeats, chapterRange, activeBeat} = module.exports;

test('all nine chapters cover every frame exactly once, including the final held answer', () => {
  let cursor = 0;
  for (const scene of [...new Set(story.beats.map((beat) => beat.scene))]) {
    const range = chapterRange(previewBeats, scene);
    assert.equal(range.from, cursor);
    const first = activeBeat(previewBeats, scene, 0);
    const last = activeBeat(previewBeats, scene, range.duration - 1);
    assert.equal(first.beat.stage, 0);
    assert.equal(last.beat.stage, story.beats.filter((beat) => beat.scene === scene).length - 1);
    cursor += range.duration;
  }
  assert.equal(cursor, totalFrames(previewBeats));
});

test('stale scripts, missing steps and partial voice-over fail closed', () => {
  assert.throws(() => validateBeats(previewBeats.slice(1)), /complete/);
  const stale = structuredClone(previewBeats); stale[0].speech = 'An obsolete opening';
  assert.throws(() => validateBeats(stale), /stale/);
  const partial = structuredClone(previewBeats);
  partial[0].audioSrc = 'inverse/audio/opening-00.wav'; partial[0].audioSha256 = 'a'.repeat(64);
  assert.throws(() => validateBeats(partial), /Partially narrated/);
});

test('both affine examples invert in both directions across negative, fractional and large inputs', () => {
  for (const input of [-1e5, -11, -0.5, 0, 3, 11, 1e5]) {
    const forward = (value) => 2 * value + 5;
    const inverse = (value) => (value - 5) / 2;
    assert.equal(forward(inverse(input)), input);
    assert.equal(inverse(forward(input)), input);
    const practice = (value) => 3 * value - 4;
    const practiceInverse = (value) => (value + 4) / 3;
    assert.ok(Math.abs(practice(practiceInverse(input)) - input) < 1e-9);
    assert.ok(Math.abs(practiceInverse(practice(input)) - input) < 1e-9);
  }
  assert.equal(Math.sqrt((-2) ** 2), 2);
  assert.notEqual(Math.sqrt((-2) ** 2), -2);
});
