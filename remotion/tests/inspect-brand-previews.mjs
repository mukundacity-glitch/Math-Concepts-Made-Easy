import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import sharp from 'sharp';
import test from 'node:test';

test('channel emblem remains visible on title cards and both cinematic backgrounds', async () => {
  // BrandHeader is at (96,64) in 1920x1080 and renders a 72x72 image.
  // Count gold ink ONLY inside this 72px square, away from caption and math.
  for (const file of ['intro','outro','diagnostics','cinematic-light','cinematic-dark']) {
    const cinematic = file.startsWith('cinematic-');
    const path='build/preview/'+file+'.png';
    const {data,info}=await sharp(readFileSync(path))
      .extract(cinematic ? {left:112,top:39,width:84,height:84} : {left:96,top:64,width:72,height:72})
      .removeAlpha().raw().toBuffer({resolveWithObject:true});
    let gold=0;
    for(let i=0;i<data.length;i+=info.channels) {
      const [r,g,b]=data.subarray(i,i+3);
      if(r>150 && g>95 && b<140 && r>b*1.4) gold++;
    }
    assert.ok(gold>65, file+' lost the gold-ink original logo: '+gold);
  }
});


test('the larger cinematic channel name contains two readable ink colors', async () => {
  for (const mode of ['light','dark']) {
    const {data,info} = await sharp('build/preview/cinematic-'+mode+'.png')
      .extract({left:220,top:60,width:800,height:50})
      .removeAlpha().raw().toBuffer({resolveWithObject:true});
    let primary=0, accent=0;
    for(let i=0;i<data.length;i+=info.channels) {
      const [r,g,b]=data.subarray(i,i+3);
      if(mode==='light') {
        if(r<45 && g<65 && b<75) primary++;
        if(r<35 && g>75 && g<130 && b>80) accent++;
      } else {
        if(r>230 && g>230 && b>220) primary++;
        if(r>200 && g>140 && g<215 && b<150) accent++;
      }
    }
    assert.ok(primary>500 && accent>250, mode+' channel branding lost a readable color');
  }
});
