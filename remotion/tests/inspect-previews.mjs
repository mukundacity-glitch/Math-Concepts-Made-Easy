import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const png = (filename) => {
  const bytes = readFileSync(filename);
  assert.ok(bytes.length > 8000, filename + ': render may be empty');
  assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  return {
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    hash: createHash('sha256').update(bytes).digest('hex'),
    size: bytes.length,
  };
};

test('title, scene shell and closing frame render distinctly at 1920x1080', () => {
  const names = ['intro', 'chapter', 'outro'];
  const frames = names.map((name) => png('build/preview/' + name + '.png'));
  for (const frame of frames) {
    assert.equal(frame.width, 1920);
    assert.equal(frame.height, 1080);
  }
  assert.equal(new Set(frames.map((frame) => frame.hash)).size, 3);
  console.log('PremiumLesson 1920x1080 preview verified:', frames.map(
    (frame, i) => names[i] + '=' + frame.size + ' bytes').join('; '));
});
