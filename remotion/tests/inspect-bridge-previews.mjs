import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import sharp from 'sharp';

test('the correct sequential Manim media sources appear in different chapters', async () => {
  const expected = [
    ['connected-concept.png', {r: 192, g: 38, b: 45}],
    ['connected-example.png', {r: 0, g: 182, b: 217}],
  ];
  for (const [file, color] of expected) {
    const png = readFileSync('build/preview/' + file);
    const pixels = await sharp(png).ensureAlpha().raw().toBuffer({resolveWithObject: true});
    assert.equal(pixels.info.width, 1920);
    assert.equal(pixels.info.height, 1080);
    // Center of the boxed media region, not the shell or sidebar.
    const x = 600;
    const y = 520;
    const offset = (y * pixels.info.width + x) * pixels.info.channels;
    const rgb = [...pixels.data.subarray(offset, offset + 3)];
    for (const [i, key] of ['r', 'g', 'b'].entries()) {
      assert.ok(Math.abs(rgb[i] - color[key]) < 45,
                file + ' wrong frame color ' + key + ': ' + rgb[i]);
    }
  }
});
