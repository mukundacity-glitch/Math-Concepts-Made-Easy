/** Package the existing composition for playback without a local server. No video export. */
import {build, stop} from 'esbuild';
import {createHash} from 'node:crypto';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {resolve, relative, sep} from 'node:path';
import {execFileSync} from 'node:child_process';
import ts from 'typescript';

const work = resolve('build/worked-example');
const props = JSON.parse(await readFile(process.argv[2] ?? `${work}/lesson.json`, 'utf8'));
const load = async () => {
  const m = {exports:{}};
  new Function('module','exports',ts.transpileModule(await readFile('src/math-board/timeline.ts','utf8'), {
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
  }).outputText)(m,m.exports);
  return m.exports;
};
const {compileBoard} = await load();
if (props.chapters.length !== 1 || !props.chapters[0].boardStates) throw new Error('Expected the worked example');
const chapter = props.chapters[0];
const plan = compileBoard(chapter.board,chapter.beats,30);
const end = (id) => chapter.beats.slice(0,chapter.beats.findIndex(b=>b.id===id)+1).reduce((n,b)=>n+b.durationInFrames,0)-15;
const highlight = plan.highlights.get('first-plus-y');
const checkpoints = {'Method':Math.floor((highlight[0]+highlight[1])/2),'Cancellation':end('add'),
  'Substitution':end('substitute'),'Verification':end('interpret')};
const assets = {};
const logo = 'branding/math-concepts-made-easy-logo.webp';
assets[logo] = 'data:image/webp;base64,'+(await readFile('public/'+logo)).toString('base64');
await mkdir(`${work}/portable-audio`,{recursive:true});
for(const beat of chapter.beats){
  if (!beat.audioSrc) {if(!props.previewMode) throw new Error('Missing prepared narration'); continue;}
  const source = resolve('public',beat.audioSrc);
  if(relative(resolve('public'),source).split(sep).includes('..')) throw new Error('Unsafe asset path');
  const bytes = await readFile(source);
  if(createHash('sha256').update(bytes).digest('hex')!==beat.audioSha256) throw new Error('Stale audio: '+beat.id);
  if(!/^[a-z0-9-]+$/.test(beat.id)) throw new Error('Unsafe beat ID');
  const output = `${work}/portable-audio/${beat.id}.ogg`;
  // Opus pre-skip preserves the PCM timeline. These are browser-preview derivatives only.
  execFileSync('ffmpeg',['-v','error','-y','-i',source,'-ac','1','-c:a','libopus','-b:a','20k',output]);
  assets[beat.audioSrc]='data:audio/ogg;base64,'+(await readFile(output)).toString('base64');
}
const bundle = await build({entryPoints:['src/preview/PortablePlayer.tsx'],bundle:true,write:false,minify:true,
  format:'iife',platform:'browser',target:'es2022',jsx:'automatic',
  define:{'process.env.NODE_ENV':'"production"',__LESSON__:JSON.stringify(props),__ASSETS__:JSON.stringify(assets),__CHECKPOINTS__:JSON.stringify(checkpoints)},
  plugins:[{name:'native-preview-audio',setup(b){
    // The native Remotion Audio player needs no decoder worker or network request.
    // Production still imports @remotion/media and is untouched by this build-only adapter.
    b.onResolve({filter:/^@remotion\/media$/},()=>({path:'native-audio',namespace:'portable'}));
    b.onLoad({filter:/.*/,namespace:'portable'},()=>({contents:"export {Audio} from 'remotion';",loader:'js',resolveDir:process.cwd()}));
  }}]});
const script=bundle.outputFiles[0].text.replace(/<\/script/gi,'<\\/script');
const css=`#elimination-player{color-scheme:light dark;color:light-dark(#172a35,#fffdf4);font-family:Arial,sans-serif}#elimination-player main{max-width:1100px;margin:auto}#elimination-player header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px}#elimination-player h1{font-size:20px;margin:0}#elimination-player header span{font-size:14px}#elimination-player nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}#elimination-player button{font:inherit;min-height:44px;padding:8px 14px;background:light-dark(#e4eeeb,#263c3c);color:inherit;border:1px solid light-dark(#8da4a4,#789090);border-radius:6px}#elimination-player button:focus-visible{outline:3px solid #00888c;outline-offset:2px}`;
const fragment=`<div id="elimination-player"></div>\n<style>${css}</style>\n<script>${script}</script>\n`;
const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Elimination lesson preview</title></head><body style="margin:0;padding:16px;background:light-dark(#f4f0e7,#20262b)">${fragment}</body></html>`;
await writeFile(`${work}/elimination-preview.html`,html);
await writeFile(`${work}/elimination-preview-fragment.html`,fragment);
console.log(JSON.stringify({file:`${work}/elimination-preview.html`,bytes:Buffer.byteLength(html),fragmentBytes:Buffer.byteLength(fragment),audioClips:Object.keys(assets).length-1,checkpoints}));

stop();
