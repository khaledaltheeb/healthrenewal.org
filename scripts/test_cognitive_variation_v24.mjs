import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { performance } from 'node:perf_hooks';

const root=process.argv[2]||'_site';
const runtime=fs.readFileSync(path.join(root,'assets/js/lab-v12.js'),'utf8');
const context={console,performance,setTimeout,clearTimeout,globalThis:null,Date,Math};context.globalThis=context;
vm.createContext(context);vm.runInContext(runtime,context,{filename:'lab-v12.js'});
const api=context.__PTERMINOLOGY_LAB_V202__;
if(!api?.makeTrial||!api?.isCorrect||!api?.estimatePoolSize)throw new Error('v202 API missing');
const dirs=fs.readdirSync(path.join(root,'cognitive-lab'),{withFileTypes:true}).filter(x=>x.isDirectory()).map(x=>x.name).sort();
if(dirs.length!==53)throw new Error(`Expected 53 cognitive tools, found ${dirs.length}`);
const errors=[];let checked=0;const rows=[];const modes=new Map();
for(const slug of dirs){
 const pageHtml=fs.readFileSync(path.join(root,'cognitive-lab',slug,'index.html'),'utf8');
 const match=pageHtml.match(/<script type="application\/json" id="lab-definition">(.*?)<\/script>/s);
 if(!match){errors.push(`${slug}: definition missing`);continue;}
 const d=JSON.parse(match[1]);modes.set(d.mode,(modes.get(d.mode)||[]).concat(slug));
 if(d.answer_mode!=='multiple-choice')errors.push(`${slug}: answer_mode`);
 if(![202,205,206,207,208,210].includes(d.question_pool_version))errors.push(`${slug}: pool version`);
 if(!Array.isArray(d.difficulty_levels)||d.difficulty_levels.length!==5)errors.push(`${slug}: difficulty levels`);
 if((d.trials_per_stage||0)<10)errors.push(`${slug}: too few trials per stage`);
 if(api.estimatePoolSize(d)<15000)errors.push(`${slug}: estimated pool too small`);
 const signatures=new Set();
 for(let stage=0;stage<5;stage++)for(const seed of [11,29,47,83,131,197])for(let index=0;index<12;index++){
  let t;
  try{t=api.makeTrial(d,stage,index,seed);}catch(error){errors.push(`${slug} s${stage} i${index}: generator threw ${error.message}`);continue;}
  checked++;
  const values=t.options.map(x=>String(typeof x==='object'?x.value:x));
  const joined=[t.study,t.prompt,t.answer,t.explanation,...values].join('|');
  if(/undefined|NaN|null/.test(joined))errors.push(`${slug} s${stage} i${index}: invalid generated value`);
  if(values.length<2)errors.push(`${slug} s${stage} i${index}: fewer than two options`);
  if(new Set(values).size!==values.length)errors.push(`${slug} s${stage} i${index}: duplicate options`);
  if(values.filter(x=>x===String(t.answer)).length!==1)errors.push(`${slug} s${stage} i${index}: answer not exactly once`);
  if(!api.isCorrect(t,t.answer))errors.push(`${slug} s${stage} i${index}: correct rejected`);
  for(const wrong of values.filter(x=>x!==String(t.answer)))if(api.isCorrect(t,wrong))errors.push(`${slug} s${stage} i${index}: wrong accepted`);
  if(t.difficulty!==stage+1)errors.push(`${slug} s${stage} i${index}: difficulty mismatch`);
  if(t.bankVersion!==203||!t.fingerprint)errors.push(`${slug} s${stage} i${index}: bank metadata`);
  if(!t.prompt||!t.explanation)errors.push(`${slug} s${stage} i${index}: incomplete content`);
  signatures.add(JSON.stringify([t.study,t.prompt,t.answer,t.stimulusWord,t.stimulusInk,values]));
 }
 if(signatures.size<4)errors.push(`${slug}: shallow pool (${signatures.size})`);
 const sameSlot=new Set([101,202,303,404,505,606].map(seed=>{try{const t=api.makeTrial(d,2,3,seed);return JSON.stringify([t.study,t.prompt,t.answer,t.stimulusWord,t.stimulusInk,t.options.map(x=>String(typeof x==='object'?x.value:x))]);}catch(error){return `ERROR:${error.message}`;}}));
 if(sameSlot.size<2)errors.push(`${slug}: session seed does not vary the same slot`);
 if(slug.startsWith('stroop')){
  const trials=Array.from({length:30},(_,i)=>api.makeTrial(d,i%5,i,700+i));
  if(trials.some(t=>!t.prompt.includes('stroop-word')||!t.prompt.includes('style="color:')))errors.push(`${slug}: ink not rendered inline`);
  if(trials.some(t=>!t.stimulusWord||!t.stimulusInk))errors.push(`${slug}: ink metadata missing`);
  if(new Set(trials.map(t=>t.stimulusInk)).size<3)errors.push(`${slug}: ink variation low`);
  if(new Set(trials.map(t=>t.stimulusWord)).size<3)errors.push(`${slug}: word variation low`);
  for(const t of trials){const expected=t.stimulusRule==='word'?t.stimulusWord:t.stimulusInk;if(String(t.answer)!==String(expected))errors.push(`${slug}: incorrect Stroop key`);}
 }
 if(slug==='working-memory-updating'){
  const byStage=Array.from({length:5},(_,stage)=>api.makeTrial(d,stage,3,900+stage));
  const operationCounts=byStage.map(t=>(t.prompt.match(/الخانة/g)||[]).length);
  if(!operationCounts.every((n,i)=>n===2+i*2))errors.push(`${slug}: update operations are not graded ${operationCounts}`);
  if(!byStage.every(t=>t.options.length>=4))errors.push(`${slug}: insufficient updating distractors`);
  if(!pageHtml.includes('data-working-memory-v205')||!pageHtml.includes('ليست اختبار IQ'))errors.push(`${slug}: safety/education note missing`);
 }
 if(slug==='prospective-memory-cues'){
  const byStage=Array.from({length:5},(_,stage)=>api.makeTrial(d,stage,4,1200+stage));
  const fillerCounts=byStage.map(t=>(t.prompt.match(/ = /g)||[]).length);
  if(!fillerCounts.every((n,i)=>n===2+i*2))errors.push(`${slug}: prospective-memory filler load is not graded ${fillerCounts}`);
  if(!byStage.every(t=>t.options.length===4))errors.push(`${slug}: expected exactly four prospective-memory choices`);
  if(!byStage.every(t=>/احفظ النية/.test(t.study)&&/ماذا يجب أن تفعل/.test(t.prompt)&&!t.prompt.includes(t.answer)))errors.push(`${slug}: delayed cue-intention contract missing`);
  if(!byStage.every((t,i)=>t.studyMs===Math.max(1800,4200-i*450)))errors.push(`${slug}: study exposure is not graded`);
  if(!pageHtml.includes('data-prospective-memory-v206')||!pageHtml.includes('ليست اختبار IQ')||!pageHtml.includes('training-only-not-diagnostic'))errors.push(`${slug}: safety/education note missing`);
 }
 if(slug==='associative-context-binding'){
  const byStage=Array.from({length:5},(_,stage)=>api.makeTrial(d,stage,5,1500+stage));
  const setSizes=byStage.map(t=>t.bindingSetSize);
  if(!setSizes.every((n,i)=>n===2+i))errors.push(`${slug}: binding set size is not graded ${setSizes}`);
  if(!byStage.every(t=>t.options.length===4&&t.study.includes(t.answer)&&!t.prompt.includes(t.answer)))errors.push(`${slug}: study-test or answer concealment contract missing`);
  if(!byStage.every((t,i)=>t.studyMs===Math.max(3000,5200-i*550)))errors.push(`${slug}: study exposure is not graded`);
  const directions=new Set(Array.from({length:40},(_,i)=>api.makeTrial(d,i%5,i,1700+i).bindingDirection));
  if(!directions.has('item-to-context')||!directions.has('context-to-item'))errors.push(`${slug}: bidirectional retrieval coverage missing ${[...directions]}`);
  if(!pageHtml.includes('data-associative-binding-v207')||!pageHtml.includes('ليست اختبار IQ')||!pageHtml.includes('training-only-not-diagnostic'))errors.push(`${slug}: safety/education note missing`);
  if(!pageHtml.includes('pubmed.ncbi.nlm.nih.gov/24660802')||!pageHtml.includes('pmc.ncbi.nlm.nih.gov/articles/PMC3784827'))errors.push(`${slug}: evidence links missing`);
 }
 if(slug==='temporal-order-memory'){
  const byStage=Array.from({length:5},(_,stage)=>api.makeTrial(d,stage,6,2000+stage));
  const lengths=byStage.map(t=>t.temporalSequenceLength);
  if(!lengths.every((n,i)=>n===3+i))errors.push(`${slug}: sequence length is not graded ${lengths}`);
  if(!byStage.every(t=>t.options.length===4&&t.study.includes(t.answer)&&!t.prompt.includes(t.answer)))errors.push(`${slug}: study-test or answer concealment contract missing`);
  if(!byStage.every((t,i)=>t.studyMs===Math.max(3000,5200-i*450)))errors.push(`${slug}: study exposure is not graded`);
  const trials=Array.from({length:60},(_,i)=>api.makeTrial(d,i%5,i,2200+i));
  const directions=new Set(trials.map(t=>t.temporalDirection));
  if(!directions.has('before')||!directions.has('after'))errors.push(`${slug}: before/after retrieval coverage missing ${[...directions]}`);
  if(trials.some(t=>!Number.isInteger(t.temporalDistance)||t.temporalDistance<1||t.temporalDistance>3))errors.push(`${slug}: invalid temporal distance`);
  if(!pageHtml.includes('data-temporal-order-v208')||!pageHtml.includes('ليست اختبار IQ')||!pageHtml.includes('training-only-not-diagnostic'))errors.push(`${slug}: safety/education note missing`);
  if(!pageHtml.includes('pubmed.ncbi.nlm.nih.gov/23563161')||!pageHtml.includes('pubmed.ncbi.nlm.nih.gov/38373517')||!pageHtml.includes('pubmed.ncbi.nlm.nih.gov/30407022'))errors.push(`${slug}: evidence links missing`);
 }
 if(slug==='visual-change-detection'){
  const byStage=Array.from({length:5},(_,stage)=>api.makeTrial(d,stage,7,2500+stage));
  const sizes=byStage.map(t=>t.visualChangeSetSize);
  if(!sizes.every((n,i)=>n===3+i))errors.push(`${slug}: visual set size is not graded ${sizes}`);
  if(!byStage.every(t=>t.options.length>=3&&t.study.includes('data-visual-change-study')&&t.prompt.includes('data-visual-change-probe')&&!t.prompt.includes(t.answer)))errors.push(`${slug}: study-test or answer concealment contract missing`);
  if(!byStage.every((t,i)=>t.studyMs===Math.max(3000,5400-i*550)))errors.push(`${slug}: study exposure is not graded`);
  if(byStage.some(t=>t.visualChangeStudySignature===t.visualChangeProbeSignature))errors.push(`${slug}: probe did not change`);
  if(byStage.some(t=>!Number.isInteger(t.visualChangePosition)||t.visualChangePosition<1||t.visualChangePosition>t.visualChangeSetSize))errors.push(`${slug}: invalid change position`);
  const trials=Array.from({length:80},(_,i)=>api.makeTrial(d,i%5,i,2700+i));
  const features=new Set(trials.map(t=>t.visualChangeFeature));
  if(!features.has('shape')||!features.has('color'))errors.push(`${slug}: shape/color change coverage missing ${[...features]}`);
  if(!pageHtml.includes('data-visual-change-v210')||!pageHtml.includes('ليست اختبار IQ')||!pageHtml.includes('training-only-not-diagnostic'))errors.push(`${slug}: safety/education note missing`);
  if(!pageHtml.includes('pubmed.ncbi.nlm.nih.gov/22099167')||!pageHtml.includes('pmc.ncbi.nlm.nih.gov/articles/PMC10197827')||!pageHtml.includes('pmc.ncbi.nlm.nih.gov/articles/PMC5632133')||!pageHtml.includes('pubmed.ncbi.nlm.nih.gov/31267436'))errors.push(`${slug}: evidence links missing`);
 }
 rows.push({slug,mode:d.mode,trialsPerStage:d.trials_per_stage,uniqueSignatures:signatures.size,estimatedPool:api.estimatePoolSize(d)});
}
for(const [mode,slugs] of modes)if(!mode)errors.push(`missing mode: ${slugs.join(',')}`);
if(!modes.has('working_memory_updating'))errors.push('working-memory updating mode missing');
if(!modes.has('prospective_memory_cues'))errors.push('prospective-memory cues mode missing');
if(!modes.has('associative_context_binding'))errors.push('associative binding mode missing');
if(!modes.has('temporal_order_memory'))errors.push('temporal order memory mode missing');
if(!modes.has('visual_change_detection'))errors.push('visual change detection mode missing');
const report={version:210,tools:dirs.length,modes:modes.size,checkedTrials:checked,totalTrials:rows.reduce((s,x)=>s+x.trialsPerStage*5,0),minimumUnique:Math.min(...rows.map(x=>x.uniqueSignatures)),errorCount:errors.length,errors:errors.slice(0,250),rows};
fs.mkdirSync(path.join(root,'api'),{recursive:true});
fs.writeFileSync(path.join(root,'api/cognitive-variation-v24.json'),JSON.stringify(report,null,2));
fs.writeFileSync(path.join(root,'api/cognitive-lab-v202-test.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));if(errors.length)process.exit(1);
