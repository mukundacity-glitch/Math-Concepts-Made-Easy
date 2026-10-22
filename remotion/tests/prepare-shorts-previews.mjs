import {readFileSync, writeFileSync} from 'node:fs';

const folder = 'build/phase4-step3-input/';
const source = JSON.parse(readFileSync(folder + 'lesson-props.json', 'utf8'));
writeFileSync(folder + 'short-selected.json', JSON.stringify({
  ...source, chapterIds: [source.chapters[1].id],
}, null, 2));
// Layout stress only. No synthetic mathematics, speech or guessed captions.
writeFileSync(folder + 'short-stress.json', JSON.stringify({
  series: 'W'.repeat(100), level: 'W'.repeat(60), title: 'W'.repeat(160),
  tagline: 'W'.repeat(240), introFrames: 60, outroFrames: 60,
  chapters: [{id: 'stress', stage: 'concept', title: 'W'.repeat(140),
    learningGoal: 'W'.repeat(260), durationInFrames: 105}],
}, null, 2));
