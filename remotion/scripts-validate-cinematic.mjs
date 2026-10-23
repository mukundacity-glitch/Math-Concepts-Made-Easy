import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
const cache = new Map();
function load(filename) {
 const full=path.resolve(filename);
 if(cache.has(full)) return cache.get(full);
 const module={exports:{}};
 const code=ts.transpileModule(fs.readFileSync(full,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
 new Function('require','module','exports',code)((name)=>load(path.resolve(path.dirname(full),name+'.ts')),module,module.exports);
 cache.set(full,module.exports);return module.exports;
}
const {cinematicFrames}=load('src/cinematic/timeline.ts');
const plans=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const list=Array.isArray(plans)?plans:[plans];
let failures=0;
for(const plan of list){try{cinematicFrames(plan);}catch(error){console.error(`Day ${plan.day}: ${error.message}`);failures++;}}
console.log(JSON.stringify({validatedLessons:list.length,failures}));
if(failures)process.exitCode=1;
