import assert from 'node:assert/strict';
import test from 'node:test';
import ts from 'typescript';
import {readFileSync} from 'node:fs';

const source = readFileSync('src/components/captionTiming.ts', 'utf8');
const js = ts.transpileModule(source, {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022},
}).outputText;
const module = {exports: {}};
new Function('module', 'exports', js)(module, module.exports);
const {captionAtFrame} = module.exports;

const pages = [
  {text:'Start with x + 2 = 5', startMs:250, endMs:900,
   timestampMs:250, confidence:null, pageBreakAfter:true},
  {text:'Subtract two from both sides.', startMs:930, endMs:1600,
   timestampMs:930, confidence:null, pageBreakAfter:true},
];

test('scene-relative speech boundaries activate and deactivate correct pages', () => {
  assert.equal(captionAtFrame(pages, 5, 30), null);
  assert.equal(captionAtFrame(pages, 15, 30)?.text, pages[0].text);
  assert.equal(captionAtFrame(pages, 27, 30), null);
  assert.equal(captionAtFrame(pages, 30, 30)?.text, pages[1].text);
  assert.equal(captionAtFrame(pages, 51, 30), null);
});

test('invalid seek frames do not display misleading stale narration', () => {
  for (const [frame, fps] of [[Number.NaN, 30], [10, 0], [Infinity, 30]]) {
    assert.equal(captionAtFrame(pages, frame, fps), null);
  }
});

test('caption lane exists outside visual panel and never restyles math', () => {
  const lane = readFileSync('src/components/CaptionLane.tsx', 'utf8');
  const frame = readFileSync('src/components/SceneFrame.tsx', 'utf8');
  assert.match(lane, /data-caption-lane="scene-local"/);
  assert.match(lane, /captionAtFrame\(captions, frame, fps\)/);
  assert.match(frame, /bottom: hasCaptions \? 258 : 134/);
  assert.match(frame, /<CaptionLane/);
  assert.match(frame, /staticFile\(chapter.media.videoSrc\)/);
  assert.doesNotMatch(lane, /MATH_PALETTE|MathTex|equation\.replace/);
});
