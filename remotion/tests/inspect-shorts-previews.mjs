import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import sharp from 'sharp';
import test from 'node:test';

const names = ['short-intro', 'short-chapter', 'short-outro', 'short-before',
  'short-concept', 'short-example', 'short-selected', 'short-stress', 'short-stress-intro'];
const pixels = async (name, area) => sharp(readFileSync('build/preview/' + name + '.png'))
  .extract(area).removeAlpha().raw().toBuffer({resolveWithObject: true});
const count = ({data, info}, predicate) => {
  let total = 0;
  for (let index = 0; index < data.length; index += info.channels) {
    if (predicate(...data.subarray(index, index + 3))) total++;
  }
  return total;
};
test('actual Shorts frames are full 1080x1920 and retain the supplied top-left emblem', async () => {
  for (const name of names) {
    const info = await sharp('build/preview/' + name + '.png').metadata();
    assert.equal(info.width, 1080, name);
    assert.equal(info.height, 1920, name);
    const logo = await pixels(name, {left: 80, top: 160, width: 80, height: 80});
    assert.ok(count(logo, (red, green, blue) => red > 150 && green > 95 && blue < 140) > 65, name);
  }
});
test('full landscape panel displays the correct scene, including a selected source chapter', async () => {
  for (const [name, cyan] of [['short-concept', false], ['short-example', true], ['short-selected', true]]) {
    const panel = await pixels(name, {left: 84, top: 612, width: 832, height: 464});
    const matches = count(panel, (red, green, blue) => cyan
      ? red < 80 && green > 100 && blue > 100
      : red > 130 && green < 100 && blue < 100);
    assert.ok(matches > 832 * 464 * .95, name);
  }
});
test('original scene-local captions are absent before speech and present during both scenes', async () => {
  const area = {left: 114, top: 1437, width: 772, height: 160};
  const white = (red, green, blue) => red > 180 && green > 180 && blue > 180;
  assert.ok(count(await pixels('short-before', area), white) < 5);
  for (const name of ['short-concept', 'short-example', 'short-selected']) {
    assert.ok(count(await pixels(name, area), white) > 100, name);
  }
});
test('stress metadata leaves the interaction rail and lower controls unobstructed', async () => {
  for (const name of ['short-chapter', 'short-stress']) {
    for (const area of [
      {left: 932, top: 280, width: 148, height: 1440},
      {left: 0, top: 1730, width: 1080, height: 190},
    ]) {
      const region = await pixels(name, area);
      assert.equal(count(region, (red, green, blue) => red !== 8 || green !== 27 || blue !== 51), 0, name);
    }
  }
});
