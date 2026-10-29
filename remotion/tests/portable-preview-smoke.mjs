/** Real offline Player regression; creates no video and uses no server. */
import {openBrowser} from '@remotion/renderer';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {readFile, writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const input = resolve('build/worked-example/elimination-preview.html');
const html = await readFile(input,'utf8');
assert.ok(Buffer.byteLength(html)<1000000,'Inline preview must remain under 1 MB');
const browser = await openBrowser('chrome');
const errors=[];
try {
  const page = await browser.newPage({context:()=>null,logLevel:'error',indent:false,pageIndex:0,
    onBrowserLog:(log)=>{if(log.type==='error')errors.push(log.text);},onLog:()=>{}});
  await page.setViewport({width:1100,height:800,deviceScaleFactor:1});
  await page.goto({url:pathToFileURL(input).href,timeout:30000});
  const wait = async (predicate) => {
    for(let attempt=0;attempt<100;attempt++) {
      if(await page.evaluate(predicate))return;
      await new Promise(r=>setTimeout(r,50));
    }
    throw new Error('Preview condition timed out');
  };
  await wait(()=>document.querySelectorAll('nav button').length===4);
  const checks=[];
  for(const name of ['Method','Cancellation','Substitution','Verification']) {
    await page.evaluate((name)=>[...document.querySelectorAll('nav button')].find(b=>b.textContent===name).click(),name);
    await new Promise(r=>setTimeout(r,120));
    const state=await page.evaluate(()=>({text:document.querySelector('svg')?.textContent,
      highlights:document.querySelectorAll('rect[fill-opacity="0.14"]').length,
      audio:[...document.querySelectorAll('audio')].filter(a=>a.src.startsWith('data:')).length,
      logo:document.querySelector('svg image')?.getAttribute('href')?.startsWith('data:image/'),
      overflow:document.documentElement.scrollWidth>innerWidth}));
    assert.ok(state.logo,'Embedded logo missing');
    assert.equal(state.overflow,false,'Desktop overflow');
    if(name==='Method')assert.equal(state.highlights,2);
    if(name==='Cancellation')assert.match(state.text,/Add both equations/);
    if(name==='Substitution')assert.match(state.text,/Substitute x = 4/);
    if(name==='Verification')assert.match(state.text,/Solution: x = 4, y = 3/);
    checks.push({checkpoint:name,...state,text:undefined});
  }
  await page.evaluate(()=>document.querySelector('nav button').click());
  await new Promise(r=>setTimeout(r,120));
  await page.evaluate(()=>{
    const play=[...document.querySelectorAll('button')].find(b=>/play/i.test(b.getAttribute('aria-label')||b.title||''));
    if(!play)throw Error('Missing play control');
    play.click();
  });
  await new Promise(r=>setTimeout(r,1200));
  const playing=await page.evaluate(()=>[...document.querySelectorAll('audio')].filter(a=>!a.paused&&a.currentTime>0).map(a=>({time:a.currentTime,ready:a.readyState,source:a.src.slice(0,15)})));
  assert.ok(playing.length>0,'Narration did not play');
  await page.setViewport({width:360,height:740,deviceScaleFactor:1});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Mobile overflow');
  assert.deepEqual(errors,[]);
  const report={offline:true,checkpoints:checks,playingAudio:playing,desktopOverflow:false,mobileOverflow:false,browserErrors:errors};
  await writeFile('build/worked-example/portable-preview-smoke.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
}finally{await browser.close({silent:true});}
