import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import sharp from 'sharp';
import test from 'node:test';

test('original channel emblem is visible at upper-left in all Full HD slides', async () => {
  // BrandHeader is at (96,64) in 1920x1080 and renders a 72x72 image.
  // Count gold ink ONLY inside this 72px square, away from caption and math.
  for (const file of ['intro','chapter','outro','diagnostics',
                      'connected-concept','connected-example']) {
    const path='build/preview/'+file+'.png';
    const {data,info}=await sharp(readFileSync(path))
      .extract({left:96,top:64,width:72,height:72})
      .removeAlpha().raw().toBuffer({resolveWithObject:true});
    let gold=0;
    for(let i=0;i<data.length;i+=info.channels) {
      const [r,g,b]=data.subarray(i,i+3);
      if(r>150 && g>95 && b<140 && r>b*1.4) gold++;
    }
    assert.ok(gold>65, file+' lost the gold-ink original logo: '+gold);
  }
});
