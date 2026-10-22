import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import test from 'node:test';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = (p) => readFileSync(join(ROOT, p), 'utf8');
const compiled = ts.transpileModule(source('src/lesson/timeline.ts'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022},
});
const module = {exports: {}};
new Function('module', 'exports', compiled.outputText)(module, module.exports);
const {buildLessonTimeline, validateLessonProps} = module.exports;

const sha = 'a'.repeat(64);
const base = () => ({
  series: 'Math Concepts Made Easy',
  level: 'Mathematics',
  title: 'Verified math lesson',
  tagline: 'Learn it',
  introFrames: 60, outroFrames: 60,
  chapters: [
    {id: 'scene-01', stage: 'concept', title: 'Concept',
     learningGoal: 'Visual reasoning', durationInFrames: 75,
     media: {
       kind: 'manim_scene', sceneId: 1,
       videoSrc: 'manim/lesson-888-aabbcc/scene_01_video.mp4',
       audioSrc: 'manim/lesson-888-aabbcc/scene_01_audio.mp3',
       videoSha256: sha, audioSha256: sha, durationSeconds: 2.5,
     }},
    {id: 'scene-02', stage: 'worked_example', title: 'Example',
     learningGoal: 'Apply', durationInFrames: 75,
     media: {
       kind: 'manim_scene', sceneId: 2,
       videoSrc: 'manim/lesson-888-aabbcc/scene_02_video.mp4',
       audioSrc: 'manim/lesson-888-aabbcc/scene_02_audio.mp3',
       videoSha256: sha, audioSha256: sha, durationSeconds: 2.5,
     }},
  ],
});

test('actual clips retain exact cumulative starts and sequence position', () => {
  assert.deepEqual(buildLessonTimeline(base()).map(
    x => [x.kind, x.start, x.durationInFrames]
  ), [
    ['intro', 0, 60], ['chapter', 60, 75],
    ['chapter', 135, 75], ['outro', 210, 60],
  ]);
});

test('missing media in a bridged package fails closed', () => {
  const p = base();
  delete p.chapters[1].media;
  assert.throws(() => validateLessonProps(p), /all chapters/);
});

test('path traversal and remote clips cannot bypass static public assets', () => {
  for (const path of ['../secrets.mp4', 'https://example.org/video.mp4',
                      '/etc/passwd', 'manim/lesson-888-aabbcc/scene_02_audio.mp3']) {
    const p = base();
    p.chapters[1].media.videoSrc = path;
    assert.throws(() => validateLessonProps(p), /unsafe or inconsistent/);
  }
});

test('wrong identity, invalid digest or mismatched duration are rejected', () => {
  const p = base(); p.chapters[1].media.sceneId = 1;
  assert.throws(() => validateLessonProps(p), /unique/);
  const brokenDigest = base(); brokenDigest.chapters[0].media.audioSha256 = '';
  assert.throws(() => validateLessonProps(brokenDigest), /digests/);
  const wrongDuration = base(); wrongDuration.chapters[0].media.durationSeconds = 4;
  assert.throws(() => validateLessonProps(wrongDuration), /duration/);
});

test('video remains silent so separately synchronized Cell-3 audio plays once', () => {
  const frame = source('src/components/SceneFrame.tsx');
  assert.match(frame, /<Video[\s\S]*?muted[\s\S]*?<Audio/);
  assert.match(frame, /staticFile\(chapter\.media\.videoSrc\)/);
  assert.match(frame, /staticFile\(chapter\.media\.audioSrc\)/);
  assert.match(frame, /objectFit="contain"/);
  assert.doesNotMatch(frame, /<BasicCaptions|<CaptionTrack/);
});
