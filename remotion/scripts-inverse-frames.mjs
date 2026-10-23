import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderStill} from '@remotion/renderer';
import {mkdir, readFile, writeFile} from 'node:fs/promises';

const story = JSON.parse(await readFile('src/inverse/storyboard.json', 'utf8'));
const serveUrl = await bundle({entryPoint: 'src/index.ts'});
const browser = await openBrowser('chrome');
const composition = await selectComposition({serveUrl, id: 'InverseFunctions', puppeteerInstance: browser});
await mkdir('build/inverse/frames', {recursive: true});
let cursor = 0;
const manifest = [];
try {
  for (const beat of story.beats) {
    const duration = Math.ceil((beat.speech.split(/\s+/).length / 2.35 + beat.holdSeconds) * 30);
    const frame = cursor + Math.min(90, duration - 1);
    const output = 'build/inverse/frames/' + beat.id + '.png';
    await renderStill({serveUrl, composition, frame, output, imageFormat: 'png', scale: .5,
      puppeteerInstance: browser, logLevel: 'error'});
    manifest.push({id: beat.id, frame, output});
    cursor += duration;
  }
  await writeFile('build/inverse/frames.json', JSON.stringify(manifest, null, 2) + '\n');
  console.log('Rendered ' + manifest.length + ' distinct mathematical states');
} finally {
  await browser.close({silent: true});
}
