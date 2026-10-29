/** Still-frame review only: never exports video or invokes a publisher. */
import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderStill} from '@remotion/renderer';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import ts from 'typescript';
const mod = {exports: {}};
new Function('module', 'exports', ts.transpileModule(await readFile('src/math-board/timeline.ts', 'utf8'), {compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
}}).outputText)(mod, mod.exports);
const {compileBoard} = mod.exports;
const inputProps = JSON.parse(await readFile(process.argv[2] ?? 'build/worked-example/lesson.json', 'utf8'));
const chapter = inputProps.chapters[0];
if (!chapter.boardStates || inputProps.chapters.length !== 1) throw new Error('Expected a single worked-example chapter');
const {board, beats} = chapter;
const plan = compileBoard(board, beats, 30);
const beatEnd = (id) => beats.slice(0, beats.findIndex((b) => b.id === id) + 1).reduce((sum,b) => sum+b.durationInFrames, 0) - 15;
const highlight = plan.highlights.get('first-plus-y');
const checkpoints = [
  ['method', Math.floor((highlight[0] + highlight[1]) / 2)],
  ['cancellation', beatEnd('add')],
  ['substitution', beatEnd('substitute')],
  ['verification', beatEnd('interpret')],
];
const out = 'build/worked-example/review';
await mkdir(out, {recursive:true});
const serveUrl = await bundle({entryPoint:'src/index.ts'});
const browser = await openBrowser('chrome');
try {
  const composition = await selectComposition({serveUrl, id:'EliminationWorkedExample', inputProps, puppeteerInstance:browser});
  for (const [name, frame] of checkpoints) {
    await renderStill({serveUrl, composition, inputProps, frame, output:`${out}/${name}.png`, puppeteerInstance:browser, logLevel:'error'});
  }
  const report = {mode: inputProps.previewMode ? 'silent-estimated-preview' : 'measured-Ryan-narration',
    frames:composition.durationInFrames, checkpoints:Object.fromEntries(checkpoints),
    narrationBeats:beats.length, allCuesResolved:true, verifiedFinalVideo:false,
    audio: beats.map((b) => ({id:b.id, durationInFrames:b.durationInFrames, wordCount:b.words?.length ?? 0, sha256:b.audioSha256 ?? null}))};
  await writeFile(`${out}/report.json`, JSON.stringify(report, null, 2)+'\n');
  console.log(JSON.stringify(report));
} finally {await browser.close({silent:true});}
