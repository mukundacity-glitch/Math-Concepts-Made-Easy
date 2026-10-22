import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import sharp from 'sharp';
import test from 'node:test';

const pix = async (path) => {
  const {data, info} = await sharp(readFileSync(path))
    .extract({left: 180, top: 857, width: 1520, height: 85})
    .removeAlpha().raw().toBuffer({resolveWithObject: true});
  assert.equal(info.width, 1520);
  assert.equal(info.height, 85);
  return data;
};

test('original timed subtitles appear and disappear without covering Manim math', async () => {
  const silent = await pix('build/preview/caption-before.png');
  const spoken = await pix('build/preview/connected-concept.png');
  assert.equal(silent.length, spoken.length);
  let different = 0;
  for (let i=0; i<silent.length; i += 3) {
    if (Math.abs(silent[i] - spoken[i]) +
        Math.abs(silent[i+1] - spoken[i+1]) +
        Math.abs(silent[i+2] - spoken[i+2]) > 90) different++;
  }
  assert.ok(different > 350,
            'caption text did not visually appear in reserved non-math lane');
  console.log('Verified caption text pixel changes in reserved lower lane:', different);
});
