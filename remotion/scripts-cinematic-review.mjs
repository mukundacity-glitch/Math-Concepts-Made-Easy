import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderStill} from '@remotion/renderer';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const day = process.argv[2] ?? '044';
const propsPath = process.argv[3] ?? `../output/cinematic/day-${day}/lesson.json`;
const inputProps = JSON.parse(await readFile(propsPath,'utf8'));
const serveUrl = await bundle({entryPoint:'src/index.ts'});
const browser = await openBrowser('chrome');
const out = `build/cinematic-review-${day}`;
await mkdir(out,{recursive:true});
try {
 const composition = await selectComposition({serveUrl,id:'CinematicLesson',inputProps,puppeteerInstance:browser});
 let cursor=0; const manifest=[];
 for(const chapter of inputProps.chapters){
  const duration=chapter.beats.reduce((sum,beat)=>sum+beat.durationInFrames,0);
  const frame=cursor + Math.max(0,duration-15);
  const output=`${out}/${chapter.id}.png`;
  await renderStill({serveUrl,composition,inputProps,frame,output,scale:.5,puppeteerInstance:browser,logLevel:'error'});
  manifest.push({chapter:chapter.id,frame,output});cursor+=duration;
 }
 await writeFile(`${out}/manifest.json`,JSON.stringify(manifest,null,2));
 console.log(JSON.stringify({frames:cursor,seconds:cursor/30,checkpoints:manifest.length}));
}finally{await browser.close({silent:true});}
