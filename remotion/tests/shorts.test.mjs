import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import test from 'node:test';
import ts from 'typescript';

const cache = new Map();
const importTS = (filename) => {
  const path = resolve(filename);
  if (cache.has(path)) return cache.get(path);
  const output = ts.transpileModule(readFileSync(path, 'utf8'), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022},
  }).outputText;
  const module = {exports: {}};
  const requireLocal = (name) => importTS(resolve(dirname(path), name + '.ts'));
  new Function('module', 'exports', 'require', output)(module, module.exports, requireLocal);
  cache.set(path, module.exports);
  return module.exports;
};
const {selectShortLesson, buildShortTimeline, getShortDurationInFrames,
       shortsCanvas, MAX_SHORT_FRAMES} = importTS('src/shorts/timeline.ts');
const {captionAtFrame} = importTS('src/components/captionTiming.ts');
const {shortLayout} = importTS('src/shorts/layout.ts');
const {fitShortText} = importTS('src/shorts/textFit.ts');
const valid = () => ({
  series: 'Math Concepts Made Easy', level: 'Grade 10', title: 'Mathematical reasoning',
  tagline: 'Build understanding step by step.', introFrames: 60, outroFrames: 60,
  chapters: [1, 2, 3].map((sceneId) => ({
    id: 'scene-' + sceneId, stage: 'concept', title: 'Concept ' + sceneId,
    learningGoal: 'Understand the method', durationInFrames: 90,
    media: {
      kind: 'manim_scene', sceneId, durationSeconds: 3,
      videoSrc: 'manim/test/scene_0' + sceneId + '_video.mp4',
      audioSrc: 'manim/test/scene_0' + sceneId + '_audio.mp3',
      videoSha256: 'a'.repeat(64), audioSha256: 'b'.repeat(64),
      captionsSha256: 'c'.repeat(64),
      captions: [{text: 'Original scene ' + sceneId, startMs: 250, endMs: 1400,
        timestampMs: 250, confidence: null, pageBreakAfter: true}],
    },
  })),
});

test('vertical registry is 1080x1920 at the media bridge frame rate', () => {
  assert.deepEqual(shortsCanvas, {width: 1080, height: 1920, fps: 30});
  assert.equal(getShortDurationInFrames(valid()), 390);
});
test('selection preserves source order, original media references and exact duration', () => {
  const props = valid();
  props.chapterIds = ['scene-3', 'scene-1'];
  const before = structuredClone(props);
  const lesson = selectShortLesson(props);
  assert.deepEqual(lesson.chapters.map(chapter => chapter.id), ['scene-1', 'scene-3']);
  assert.equal(lesson.chapters[0], props.chapters[0]);
  assert.equal(lesson.chapters[1].media.captions, props.chapters[2].media.captions);
  assert.deepEqual(buildShortTimeline(props).map(segment => [segment.kind, segment.start, segment.durationInFrames]),
    [['intro', 0, 60], ['chapter', 60, 90], ['chapter', 150, 90], ['outro', 240, 60]]);
  assert.deepEqual(props, before);
});
test('unknown, empty, malformed or duplicate selections cannot silently export wrong material', () => {
  for (const chapterIds of [[], ['missing'], ['scene-1', 'scene-1'], 'scene-1', [null]]) {
    assert.throws(() => selectShortLesson({...valid(), chapterIds}), /chapterIds/);
  }
});
test('overlong shorts fail without trimming; the exact editorial boundary succeeds', () => {
  const props = valid();
  props.chapters = [props.chapters[0]];
  props.chapters[0].durationInFrames = MAX_SHORT_FRAMES - 120;
  props.chapters[0].media.durationSeconds = (MAX_SHORT_FRAMES - 120) / 30;
  assert.equal(getShortDurationInFrames(props), MAX_SHORT_FRAMES);
  props.chapters[0].durationInFrames++;
  props.chapters[0].media.durationSeconds = props.chapters[0].durationInFrames / 30;
  assert.throws(() => getShortDurationInFrames(props), /180-second/);
});
test('connected media requires original captions and source validation precedes selection', () => {
  const props = valid();
  delete props.chapters[0].media.captions;
  delete props.chapters[0].media.captionsSha256;
  assert.throws(() => selectShortLesson(props), /partially captioned/);
  for (const chapter of props.chapters) {
    delete chapter.media.captions;
    delete chapter.media.captionsSha256;
  }
  assert.throws(() => selectShortLesson(props), /original word-timed/);
  const corrupt = valid();
  corrupt.chapterIds = ['scene-1'];
  corrupt.chapters[1].media.videoSrc = '../../outside.mp4';
  assert.throws(() => selectShortLesson(corrupt), /unsafe/);
});
test('captions reset to the selected chapter clock after skipping source chapters', () => {
  const props = valid();
  props.chapterIds = ['scene-2'];
  const chapter = buildShortTimeline(props)[1];
  assert.equal(captionAtFrame(chapter.chapter.media.captions, 64 - chapter.start, 30), null);
  assert.equal(captionAtFrame(chapter.chapter.media.captions, 68 - chapter.start, 30)?.text, 'Original scene 2');
  assert.equal(captionAtFrame(chapter.chapter.media.captions, 102 - chapter.start, 30), null);
});
test('media, learning focus, captions and progress occupy disjoint safe areas', () => {
  assert.equal(shortLayout.width / shortLayout.mediaHeight, 16 / 9);
  assert.ok(shortLayout.left >= 80);
  assert.ok(shortLayout.left + shortLayout.width <= shortsCanvas.width - 160);
  assert.ok(shortLayout.mediaTop + shortLayout.mediaHeight < shortLayout.focusTop);
  assert.ok(shortLayout.focusTop + shortLayout.focusHeight < shortLayout.captionTop);
  assert.ok(shortLayout.captionTop + shortLayout.captionHeight < shortLayout.progressTop);
  assert.ok(shortLayout.progressTop + 40 <= shortsCanvas.height - 200);
});
test('long titles, goals, and original caption pages fit without losing characters', () => {
  const measure = (text, size) => [...text].length * size;
  for (const [text, width, height, fontSize, lineHeight] of [
    ['W'.repeat(160), 840, 600, 84, 1.12],
    ['Wide mathematical idea '.repeat(6).slice(0, 140), 840, 190, 64, 1.12],
    ['W'.repeat(260), 840, 242, 40, 1.25],
    ['Original caption words '.repeat(6).slice(0, 125), 774, 162, 44, 1.2],
  ]) {
    const fit = fitShortText(text, width, height, fontSize, lineHeight, measure);
    assert.ok(fit.lines.length * fit.fontSize * lineHeight <= height);
    assert.ok(fit.lines.every(line => measure(line, fit.fontSize) <= width));
    assert.equal(fit.lines.join('').replaceAll(' ', ''), text.replaceAll(' ', ''));
  }
  assert.throws(() => fitShortText('unreadable', 1, 1, 44, 1.2, measure), /cannot fit/);
});
test('vertical layout retains contained video, one narration and the canonical emblem', () => {
  const source = readFileSync('src/shorts/ShortSlides.tsx', 'utf8');
  assert.match(source, /objectFit="contain"/);
  assert.match(source, /videoSrc\)\} muted/);
  assert.equal((source.match(/<Audio /g) ?? []).length, 1);
  assert.match(source, /captionAtFrame\(chapter.media\?\.captions/);
  assert.match(source, /<BrandLogo size=\{80\}/);
  assert.doesNotMatch(source, /playbackRate|trimBefore|uploader|MATH_PALETTE/);
});
