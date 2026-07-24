import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { performance } from 'node:perf_hooks';

const root=process.argv[2]||'_site';
const expectedTools=53;
const stagesExpected=5;
const seeds=[11,29,47,83,131,197,263,347,431,557,683,811,947,1087,1231,1429];
const indices=Array.from({length:32},(_,i)=>i);
const sessionsPerTool=40;
const sessionCushion=3;
const runtime=fs.readFileSync(path.join(root,'assets/js/lab-v12.js'),'utf8');
const context={console,performance,setTimeout,clearTimeout,globalThis:null,Date,Math};context.globalThis=context;
vm.createContext(context);vm.runInContext(runtime,context,{filename:'lab-v12.js'});
const api=context.__PTERMINOLOGY_LAB_V202__;
if(!api?.makeTrial||!api?.isCorrect)throw new Error('Cognitive v202 API is unavailable');

const clean=value=>String(value??'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const optionValue=value=>String(typeof value==='object'?value.value:value);
const semanticSignature=trial=>JSON.stringify([
 clean(trial.study),clean(trial.prompt),String(trial.answer),
 trial.stimulusWord||'',trial.stimulusInk||'',trial.stimulusRule||'',
 trial.bindingDirection||'',trial.temporalDirection||'',trial.visualChangeFeature||'',
 trial.visualChangeSetSize||'',trial.visualChangePosition||'',trial.updateOperationCount||'',
 [...trial.options.map(optionValue)].sort()
]);
const promptSignature=trial=>JSON.stringify([
 clean(trial.study),clean(trial.prompt),String(trial.answer),
 trial.stimulusWord||'',trial.stimulusInk||'',trial.stimulusRule||'',
 trial.bindingDirection||'',trial.temporalDirection||'',trial.visualChangeFeature||''
]);
const invalidPattern=/\b(?:undefined|NaN|null)\b/;

const dirs=fs.readdirSync(path.join(root,'cognitive-lab'),{withFileTypes:true})
 .filter(entry=>entry.isDirectory()).map(entry=>entry.name).sort();
if(dirs.length!==expectedTools)throw new Error(`Expected ${expectedTools} cognitive tools, found ${dirs.length}`);

const errors=[];
const rows=[];
let generatedTrials=0;
let simulatedSessionTrials=0;
for(const slug of dirs){
 const pagePath=path.join(root,'cognitive-lab',slug,'index.html');
 const html=fs.readFileSync(pagePath,'utf8');
 const match=html.match(/<script type="application\/json" id="lab-definition">(.*?)<\/script>/s);
 if(!match){errors.push(`${slug}: missing lab definition`);continue;}
 const definition=JSON.parse(match[1]);
 const perStage=Math.max(10,Number(definition.trials_per_stage)||10);
 const stages=Number(definition.stages)||0;
 const toolErrors=[];
 const stageRows=[];
 const totalSemantic=new Set();
 const totalPrompts=new Set();
 const totalFingerprints=new Set();
 const optionCounts=new Set();
 const answerCounts=new Map();
 const difficultySeen=new Set();

 if(stages!==stagesExpected)toolErrors.push(`stages ${stages} != ${stagesExpected}`);
 if(definition.answer_mode!=='multiple-choice')toolErrors.push('answer mode is not multiple-choice');
 if(perStage<10)toolErrors.push(`trials per stage ${perStage} < 10`);

 for(let stage=0;stage<stagesExpected;stage++){
  const semantic=new Set();
  const prompts=new Set();
  const fingerprints=new Set();
  let correctChecks=0,wrongChecks=0;
  for(const seed of seeds){
   for(const index of indices){
    let trial;
    try{trial=api.makeTrial(definition,stage,index,seed);}catch(error){toolErrors.push(`stage ${stage+1} generator threw: ${error.message}`);continue;}
    generatedTrials++;
    difficultySeen.add(trial.difficulty);
    const values=trial.options.map(optionValue);
    optionCounts.add(values.length);
    answerCounts.set(String(trial.answer),(answerCounts.get(String(trial.answer))||0)+1);
    const joined=[trial.study,trial.prompt,trial.answer,trial.explanation,...values].join('|');
    if(invalidPattern.test(joined))toolErrors.push(`stage ${stage+1}: invalid generated token`);
    if(!clean(trial.prompt))toolErrors.push(`stage ${stage+1}: empty prompt`);
    if(!clean(trial.explanation))toolErrors.push(`stage ${stage+1}: empty explanation`);
    if(values.length<2)toolErrors.push(`stage ${stage+1}: fewer than two choices`);
    if(new Set(values).size!==values.length)toolErrors.push(`stage ${stage+1}: duplicate choices`);
    if(values.filter(value=>value===String(trial.answer)).length!==1)toolErrors.push(`stage ${stage+1}: answer does not occur exactly once`);
    if(!api.isCorrect(trial,trial.answer))toolErrors.push(`stage ${stage+1}: correct answer rejected`);else correctChecks++;
    for(const wrong of values.filter(value=>value!==String(trial.answer))){
     if(api.isCorrect(trial,wrong))toolErrors.push(`stage ${stage+1}: wrong answer accepted`);else wrongChecks++;
    }
    if(trial.difficulty!==stage+1)toolErrors.push(`stage ${stage+1}: difficulty metadata ${trial.difficulty}`);
    if(!trial.fingerprint)toolErrors.push(`stage ${stage+1}: missing fingerprint`);
    semantic.add(semanticSignature(trial));
    prompts.add(promptSignature(trial));
    fingerprints.add(String(trial.fingerprint));
   }
  }
  const minimumUnique=Math.max(perStage*sessionCushion,30);
  const minimumPrompts=Math.max(perStage*2,20);
  if(fingerprints.size<minimumUnique)toolErrors.push(`stage ${stage+1}: fingerprint bank ${fingerprints.size} < ${minimumUnique}`);
  if(semantic.size<minimumUnique)toolErrors.push(`stage ${stage+1}: semantic bank ${semantic.size} < ${minimumUnique}`);
  if(prompts.size<minimumPrompts)toolErrors.push(`stage ${stage+1}: prompt bank ${prompts.size} < ${minimumPrompts}`);
  for(const value of semantic)totalSemantic.add(value);
  for(const value of prompts)totalPrompts.add(value);
  for(const value of fingerprints)totalFingerprints.add(value);
  stageRows.push({
   stage:stage+1,samples:seeds.length*indices.length,
   requiredUniqueTrials:minimumUnique,requiredUniquePrompts:minimumPrompts,
   uniqueFingerprints:fingerprints.size,uniqueSemanticTrials:semantic.size,uniquePrompts:prompts.size,
   correctChecks,wrongChecks
  });
 }

 let sessionDuplicates=0,retryExhaustions=0;
 for(let session=0;session<sessionsPerTool;session++){
  const sessionSeed=(0x9e3779b9*(session+1)+slug.length*1009)>>>0;
  const seen=new Set();
  for(let stage=0;stage<stagesExpected;stage++){
   for(let index=0;index<perStage;index++){
    let trial=api.makeTrial(definition,stage,index,sessionSeed);
    let retries=0;
    while(retries<30&&seen.has(String(trial.fingerprint))){
     retries++;
     trial=api.makeTrial(definition,stage,index+997*retries,sessionSeed);
    }
    simulatedSessionTrials++;
    if(seen.has(String(trial.fingerprint))){sessionDuplicates++;retryExhaustions++;}
    seen.add(String(trial.fingerprint));
   }
  }
 }
 if(sessionDuplicates)toolErrors.push(`session repeat guard exhausted ${sessionDuplicates} times in ${sessionsPerTool} sessions`);
 if(![1,2,3,4,5].every(level=>difficultySeen.has(level)))toolErrors.push(`difficulty coverage incomplete: ${[...difficultySeen].sort()}`);

 const cumulativeStageFingerprints=stageRows.reduce((sum,row)=>sum+row.uniqueFingerprints,0);
 const cumulativeStageSemantic=stageRows.reduce((sum,row)=>sum+row.uniqueSemanticTrials,0);
 const cumulativeStagePrompts=stageRows.reduce((sum,row)=>sum+row.uniquePrompts,0);
 const deduped=[...new Set(toolErrors)];
 for(const error of deduped)errors.push(`${slug}: ${error}`);
 rows.push({
  slug,title:definition.title,mode:definition.mode,category:definition.category,
  trialsPerStage:perStage,sessionTrials:perStage*stagesExpected,
  samplesPerStage:seeds.length*indices.length,totalSamples:seeds.length*indices.length*stagesExpected,
  globallyUniqueFingerprints:totalFingerprints.size,globallyUniqueSemanticTrials:totalSemantic.size,globallyUniquePrompts:totalPrompts.size,
  cumulativeStageFingerprints,cumulativeStageSemantic,cumulativeStagePrompts,
  optionCounts:[...optionCounts].sort((a,b)=>a-b),distinctAnswers:answerCounts.size,
  sessionsSimulated:sessionsPerTool,sessionDuplicates,retryExhaustions,
  stages:stageRows,errorCount:deduped.length,errors:deduped,
  status:deduped.length?'failed':'passed'
 });
}

const report={
 version:211,status:errors.length?'failed':'passed',tools:dirs.length,
 toolsPassed:rows.filter(row=>row.status==='passed').length,
 toolsFailed:rows.filter(row=>row.status==='failed').length,
 generatedTrials,simulatedSessionTrials,
 empiricalBankFloorPerStage:30,empiricalPromptFloorPerStage:20,
 sessionsPerTool,sessionRepeatGuardRequired:true,
 errorCount:errors.length,errors:errors.slice(0,500),rows
};
fs.mkdirSync(path.join(root,'api'),{recursive:true});
fs.writeFileSync(path.join(root,'api/cognitive-bank-audit-v211.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(errors.length)process.exit(1);
