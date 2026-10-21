const fs=require('node:fs');
const katex=require('katex');
const entries=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
let failures=0;
for(const entry of entries){
  try{
    if(/[\u0000-\u001f]/u.test(entry.latex))throw new Error('control character in math');
    katex.renderToString(entry.latex,{throwOnError:true,strict:'ignore'});
  }catch(error){console.error(`${entry.location}: ${error.message}`);failures++;}
}
console.log(`Validated ${entries.length} math expressions; ${failures} failures.`);
process.exitCode=failures?1:0;
