import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { performance } from 'node:perf_hooks';

const root=process.argv[2]||'_site';
const runtime=fs.readFileSync(path.join(root,'assets/js/lab-v12.js'),'utf8');
const context={console,performance,setTimeout,clearTimeout,globalThis:null,Date,Math};context.globalThis=context;
vm.createContext(context);vm.runInContext(runtime,context,{filename:'lab-v12.js'});
const api=context.__PTERMINOLOGY_LAB_V202__;
if(!api?.makeTrial||!api?.isCorrect)throw new Error('Cognitive API unavailable');
const targetModes=new Map([
 ['choice_reaction',{field:'difficultyLoad',expected:[1,2,3,4,5],extra:(t,s)=>t.ruleSwitchSetSize===[1,1,1,2,3][s]&&t.choiceCount>=[4,5,5,6,7][s]}],
 ['visual_reaction',{field:'difficultyLoad',expected:[1,2,3,4,5],extra:(t,s)=>t.ruleSwitchSetSize===[1,1,1,2,3][s]&&t.choiceCount>=[4,5,5,6,7][s]}],
 ['response_inhibition',{field:'inhibitionRuleComplexity',expected:[1,2,3,4,5],extra:(t,s)=>t.ruleClauses===[1,2,2,3,4][s]}],
 ['conditional_reasoning',{field:'inferenceComplexity',expected:[1,2,3,4,5],extra:(t,s)=>typeof t.inferenceType==='string'}],
 ['context_clues',{field:'contextTier',expected:[1,2,3,4,5]}],
 ['emotion_recognition',{field:'emotionTier',expected:[1,2,3,4,5]}],
 ['perspective_taking',{field:'difficultyLoad',expected:[1,2,3,4,5],extra:(t,s)=>t.perspectiveOrder===[1,1,1,2,2][s]&&t.narrativeMoves===[1,1,2,2,3][s]}],
 ['planning_steps',{field:'planningDemand',expected:[1,2,3,4,5]}],
 ['priority_planning',{field:'priorityDemand',expected:[1,2,3,4,5]}],
 ['problem_solving',{field:'problemPhase',expected:[1,2,3,4,5]}],
 ['word_categories',{field:'difficultyLoad',expected:[1,2,3,4,5],extra:(t,s)=>t.categoryCueCount===[2,3,4,5,6][s]&&t.distractorCloseness===s+1}],
 ['semantic_fluency',{field:'difficultyLoad',expected:[1,2,3,4,5],extra:(t,s)=>t.semanticSetSize===[3,3,4,5,6][s]&&t.semanticDistractorCloseness===s+1}],
 ['social_scenarios',{field:'socialNuance',expected:[1,2,3,4,5]}],
 ['verbal_analogy',{field:'analogyTier',expected:[1,2,3,4,5]}],
]);
const dirs=fs.readdirSync(path.join(root,'cognitive-lab'),{withFileTypes:true}).filter(e=>e.isDirectory()).map(e=>e.name).sort();
if(dirs.length!==53)throw new Error(`Expected 53 tools, found ${dirs.length}`);
const errors=[],rows=[];let generated=0,correctChecks=0,wrongChecks=0;
const seeds=[17,31,53,79,101,137,173,211];
const indices=Array.from({length:16},(_,i)=>i);
const clean=v=>String(v??'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const val=o=>String(typeof o==='object'?o.value:o);
for(const slug of dirs){
 const html=fs.readFileSync(path.join(root,'cognitive-lab',slug,'index.html'),'utf8');
 const match=html.match(/<script type="application\/json" id="lab-definition">(.*?)<\/script>/s);
 if(!match){errors.push(`${slug}: definition missing`);continue;}
 const d=JSON.parse(match[1]),check=targetModes.get(d.mode),stageRows=[];
 for(let stage=0;stage<5;stage++){
  const semantic=new Set(),prompts=new Set(),signals=new Set();
  for(const seed of seeds)for(const index of indices){
   let t;try{t=api.makeTrial(d,stage,index,seed);}catch(e){errors.push(`${slug} stage ${stage+1}: ${e.message}`);continue;}
   generated++;
   const values=t.options.map(val),answer=String(t.answer);
   if(!clean(t.prompt)||!clean(t.explanation))errors.push(`${slug} stage ${stage+1}: empty content`);
   if(values.filter(x=>x===answer).length!==1)errors.push(`${slug} stage ${stage+1}: answer cardinality`);
   if(new Set(values).size!==values.length)errors.push(`${slug} stage ${stage+1}: duplicate options`);
   if(!api.isCorrect(t,answer))errors.push(`${slug} stage ${stage+1}: correct rejected`);else correctChecks++;
   for(const wrong of values.filter(x=>x!==answer)){if(api.isCorrect(t,wrong))errors.push(`${slug} stage ${stage+1}: wrong accepted`);else wrongChecks++;}
   if(t.difficulty!==stage+1)errors.push(`${slug} stage ${stage+1}: generic difficulty mismatch`);
   semantic.add(JSON.stringify([clean(t.study),clean(t.prompt),answer,[...values].sort(),t.stimulusWord||'',t.stimulusInk||'',t.ruleDomain||'',t.inferenceType||'']));
   prompts.add(JSON.stringify([clean(t.study),clean(t.prompt)]));
   if(check){
    if(t.difficultyLoad!==stage+1)errors.push(`${slug} stage ${stage+1}: difficultyLoad ${t.difficultyLoad}`);
    if(t[check.field]!==check.expected[stage])errors.push(`${slug} stage ${stage+1}: ${check.field} ${t[check.field]}`);
    if(check.extra&&!check.extra(t,stage))errors.push(`${slug} stage ${stage+1}: mode-specific progression signal`);
    if(!clean(t.difficultyDescriptor))errors.push(`${slug} stage ${stage+1}: missing difficulty descriptor`);
    signals.add(JSON.stringify([t.difficultyLoad,t[check.field],t.ruleSwitchSetSize,t.choiceCount,t.ruleClauses,t.inferenceType,t.perspectiveOrder,t.narrativeMoves,t.categoryCueCount,t.semanticSetSize]));
   }
  }
  if(check&&semantic.size<30)errors.push(`${slug} stage ${stage+1}: semantic bank ${semantic.size} < 30`);
  if(check&&prompts.size<30)errors.push(`${slug} stage ${stage+1}: prompt bank ${prompts.size} < 30`);
  stageRows.push({stage:stage+1,uniqueSemantic:semantic.size,uniquePrompts:prompts.size,signals:[...signals]});
 }
 if(check){
  const fingerprints=stageRows.map(x=>x.signals[0]).filter(Boolean);
  if(new Set(fingerprints).size<5)errors.push(`${slug}: stage progression signatures are not distinct`);
 }
 rows.push({slug,mode:d.mode,graded:!!check,stages:stageRows});
}
for(const mode of targetModes.keys())if(!rows.some(r=>r.mode===mode))errors.push(`Missing graded mode: ${mode}`);
const deduped=[...new Set(errors)];
const report={version:212,status:deduped.length?'failed':'passed',tools:dirs.length,gradedModes:targetModes.size,generatedTrials:generated,correctChecks,wrongChecks,errorCount:deduped.length,errors:deduped.slice(0,500),rows};
fs.mkdirSync(path.join(root,'api'),{recursive:true});
fs.writeFileSync(path.join(root,'api/cognitive-difficulty-audit-v212.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(deduped.length)process.exit(1);
