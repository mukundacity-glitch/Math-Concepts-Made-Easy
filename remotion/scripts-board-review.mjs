import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderStill} from '@remotion/renderer';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
const inputProps = JSON.parse(await readFile('build/inverse/lesson.json', 'utf8'));
const serveUrl = await bundle({entryPoint: 'src/index.ts'});
const browser = await openBrowser('chrome');
await mkdir('build/inverse/board-review', {recursive: true});
const composition = await selectComposition({serveUrl, id: 'InverseFunctions', inputProps, puppeteerInstance: browser});
const targets = [['machine-00','three',0,.4], ['machine-00','two',0,.6],
  ['machine-02','add',0,.4], ['machine-02','eleven',0,.6], ['notation-02','times',0,.25],
  ['notation-02','twentyseven',1,.8], ['domain-01','four',0,.3], ['domain-01','four',1,.8],
  ['algebra-00', 'y', 0, 0.25], ['algebra-00','five',0,.6],
  ['algebra-02','both',0,.7], ['algebra-03','cancel',0,.6], ['algebra-03','y',0,1],
  ['algebra-05','cancel',0,.6], ['algebra-08','three',0,1], ['verify-02','cancels',0,1],
  ['verify-03','leaving',0,1], ['verify-06','is',0,1], ['practice-03','sides',0,.8],
  ['practice-03','three',0,1], ['practice-05','four',1,1], ['practice-06','eight',0,1]];
const manifest=[];
try {
 for (const [id, word, nth, after] of targets) {
  const index = inputProps.beats.findIndex(b=>b.id === id);
  const beat = inputProps.beats[index];
  const spoken = beat.words.filter(w=>w.text.toLowerCase().replace(/\W/g,'') === word)[nth];
  if(!spoken) throw new Error(id+' missing '+word+' #'+nth);
  const frame = inputProps.beats.slice(0,index).reduce((s,b)=>s+b.durationInFrames,0) + Math.round((spoken.start+after)*30);
  const output = `build/inverse/board-review/${id}-${word}-${nth}.png`;
  await renderStill({serveUrl, composition, inputProps, frame, output, scale:.5, puppeteerInstance: browser, logLevel:'error'});
  manifest.push({id,word,nth,frame,output});
 }
 await writeFile('build/inverse/board-review/manifest.json', JSON.stringify(manifest,null,2));
 console.log('Reviewed frames ready: '+manifest.length);
} finally {await browser.close({silent:true});}
