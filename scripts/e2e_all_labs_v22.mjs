import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base=process.env.AUDIT_BASE_URL||'http://127.0.0.1:8000/';
const outDir=process.env.AUDIT_OUT_DIR||'_site/api';
fs.mkdirSync(outDir,{recursive:true});
const definitions=(root)=>fs.readdirSync(path.join('_site',root),{withFileTypes:true}).filter(x=>x.isDirectory()).map(x=>x.name).sort();
const assessments=definitions('assessment-lab'),cognitive=definitions('cognitive-lab');
const errors=[],rows=[];
const HEADLESS_AUDIO_RENDERER=/The AudioContext encountered an error from the audio device or the WebAudio renderer\.?/i;
const STROOP_RGB={
  'أحمر':'rgb(180, 35, 24)',
  'أزرق':'rgb(23, 92, 211)',
  'أخضر':'rgb(6, 118, 71)',
  'برتقالي':'rgb(181, 71, 8)',
  'بنفسجي':'rgb(105, 65, 198)',
  'تركواز':'rgb(8, 126, 139)'
};

async function contextFor(browser,profile){
  return browser.newContext({
    viewport:profile==='mobile'?{width:390,height:844}:{width:1440,height:900},
    locale:'ar-JO',colorScheme:'light',reducedMotion:'reduce'
  });
}

async function common(page,route,profile){
  const consoleErrors=[],pageErrors=[],failed=[],ignoredEnvironmentSignals=[];
  page.on('console',m=>{
    if(m.type()!=='error')return;
    const text=m.text();
    if(route==='cognitive-lab/auditory-symbol/'&&HEADLESS_AUDIO_RENDERER.test(text)){
      ignoredEnvironmentSignals.push(text);
      return;
    }
    consoleErrors.push(text);
  });
  page.on('pageerror',e=>pageErrors.push(String(e)));
  page.on('requestfailed',r=>{if(r.url().startsWith(base))failed.push(`${r.method()} ${r.url()} ${r.failure()?.errorText||''}`)});
  const response=await page.goto(new URL(route,base).href,{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForSelector('[data-v12-lab]',{timeout:10000});
  const layout=await page.evaluate(()=>({h1:document.querySelectorAll('h1').length,scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,dir:document.documentElement.dir,lang:document.documentElement.lang}));
  if(!response?.ok())errors.push(`${profile}:${route} HTTP ${response?.status()}`);
  if(layout.h1!==1||layout.scrollWidth>layout.clientWidth+4||layout.dir!=='rtl'||layout.lang!=='ar')errors.push(`${profile}:${route} layout ${JSON.stringify(layout)}`);
  return{consoleErrors,pageErrors,failed,layout,ignoredEnvironmentSignals};
}

async function runAssessment(browser,slug,profile){
  const ctx=await contextFor(browser,profile),page=await ctx.newPage();
  const route=`assessment-lab/${slug}/`;const baseRow={kind:'assessment',slug,profile,route};
  try{
    const signals=await common(page,route,profile);
    const def=await page.locator('#lab-definition').evaluate(n=>JSON.parse(n.textContent));
    const total=def.questions.length;let guardChecked=false,stages=0;
    while(true){
      stages++;if(stages>10)throw new Error('stage loop');
      if(!guardChecked){await page.locator('button.next').click();const visible=await page.locator('.lab-inline-error:not([hidden])').count();if(!visible)throw new Error('missing unanswered guard');guardChecked=true;}
      const fields=page.locator('fieldset.question');const count=await fields.count();
      for(let i=0;i<count;i++)await fields.nth(i).locator('input[type=radio]').last().check();
      await page.locator('button.interim').click();
      if(!(await page.locator('.result-card:not([hidden])').count()))throw new Error('interim result absent');
      const label=await page.locator('.stage-meta strong').innerText();
      const final=label.includes('المرحلة')&&await page.locator('button.next').innerText().then(t=>t.includes('إنهاء'));
      await page.locator('button.next').click();if(final)break;await page.waitForTimeout(20);
    }
    const result=await page.locator('.result-card').innerText();
    if(!result.includes('النتيجة النهائية')||!result.includes(`${total} من ${total}`))throw new Error(`incomplete final result: ${result.slice(0,160)}`);
    if(/تشخيص مؤكد|تم تشخيصك|لديك اضطراب/.test(result))throw new Error('diagnostic claim');
    await page.reload({waitUntil:'domcontentloaded'});await page.waitForSelector('[data-v12-lab]');
    const saved=await page.locator('.stage-meta span').innerText();if(!saved.includes(`${total}/${total}`))throw new Error(`resume failed: ${saved}`);
    const allSignals=[...signals.consoleErrors,...signals.pageErrors,...signals.failed];if(allSignals.length)throw new Error(allSignals.join(' | '));
    rows.push({...baseRow,status:'passed',questions:total,stages,resultChars:result.length});
  }catch(e){errors.push(`${profile}:${route} ${e}`);rows.push({...baseRow,status:'failed',error:String(e)});}finally{await ctx.close();}
}

async function runCognitive(browser,slug,profile){
  const ctx=await contextFor(browser,profile);
  await ctx.addInitScript(()=>{const native=window.setTimeout;window.setTimeout=(fn,ms,...args)=>native(fn,Math.min(Number(ms)||0,8),...args);});
  const page=await ctx.newPage();const route=`cognitive-lab/${slug}/`;const baseRow={kind:'cognitive',slug,profile,route};
  try{
    const signals=await common(page,route,profile);
    const def=await page.locator('#lab-definition').evaluate(n=>JSON.parse(n.textContent));
    const stages=def.stages||5,per=def.trials_per_stage||6,total=stages*per;
    let correctUiChecks=0,wrongUiChecks=0,stroopChecks=0,visualChangeChecks=0;
    const stroopRules=new Set(),stroopInks=new Set(),stroopWords=new Set(),visualChangeFeatures=new Set(),visualChangeSizes=new Set();
    for(let i=0;i<total;i++){
      const start=page.locator('button.start');if(await start.count())await start.click();
      await page.waitForSelector('button.choice-button',{timeout:5000});
      const choices=page.locator('button.choice-button');
      const count=await choices.count();
      if(slug==='simple-reaction'){
        if(count!==1)throw new Error(`simple reaction choices ${count} at ${i}`);
        const label=(await choices.first().innerText()).trim();if(label!=='اضغط الآن')throw new Error(`simple reaction label ${label}`);
      }else if(count<2)throw new Error(`fewer than two choices at ${i}`);
      if(slug.startsWith('stroop')){
        const visual=await page.locator('.stroop-word').evaluate(node=>({
          word:node.dataset.word||'',ink:node.dataset.ink||'',computed:getComputedStyle(node).color,
          prompt:node.closest('.prompt,.question,.trial-card')?.textContent||node.parentElement?.textContent||''
        }));
        const expected=STROOP_RGB[visual.ink];
        if(!visual.word||!visual.ink||visual.word===visual.ink)throw new Error(`invalid Stroop stimulus at ${i}: ${JSON.stringify(visual)}`);
        if(!expected||visual.computed!==expected)throw new Error(`Stroop ink mismatch at ${i}: expected ${expected}, got ${visual.computed}`);
        const rule=visual.prompt.includes('لون الحبر')?'ink':visual.prompt.includes('معنى الكلمة')?'word':'';
        if(!rule)throw new Error(`missing Stroop rule at ${i}`);
        const optionTexts=await choices.allTextContents();
        const expectedAnswer=rule==='ink'?visual.ink:visual.word;
        if(optionTexts.filter(x=>x.trim()===expectedAnswer).length!==1)throw new Error(`Stroop answer option mismatch at ${i}`);
        stroopRules.add(rule);stroopInks.add(visual.ink);stroopWords.add(visual.word);stroopChecks++;
      }
      if(slug==='visual-change-detection'){
        const visual=await page.evaluate(()=>{
          const probe=document.querySelector('[data-visual-change-probe]');
          const grid=probe?.querySelector('[data-visual-change-grid]');
          const items=[...(grid?.querySelectorAll('.visual-change-item')||[])];
          return{
            probePresent:Boolean(probe),setSize:Number(grid?.dataset.setSize||0),items:items.length,
            ariaComplete:items.every(node=>Boolean(node.getAttribute('aria-label'))),prompt:probe?.textContent||''
          };
        });
        if(!visual.probePresent||visual.setSize<3||visual.items!==visual.setSize||!visual.ariaComplete)throw new Error(`invalid visual-change rendering at ${i}: ${JSON.stringify(visual)}`);
        const stage=Math.floor(i/per);
        if(visual.setSize!==3+stage)throw new Error(`visual-change rendered set size ${visual.setSize} at stage ${stage}`);
        const optionTexts=(await choices.allTextContents()).map(x=>x.trim());
        if(new Set(optionTexts).size!==optionTexts.length)throw new Error(`visual-change duplicate rendered choices at ${i}`);
        visualChangeSizes.add(visual.setSize);visualChangeChecks++;
      }
      const snapshot=await choices.nth(i%count).evaluate(node=>{
        node.click();
        const buttons=[...document.querySelectorAll('button.choice-button')];
        const feedback=document.querySelector('.trial-feedback')?.textContent||'';
        return{
          correctCount:buttons.filter(x=>x.classList.contains('is-correct')).length,
          selectedCorrect:node.classList.contains('is-correct'),
          selectedWrong:node.classList.contains('is-wrong'),
          feedback
        };
      });
      if(snapshot.correctCount!==1)throw new Error(`correct marker count ${snapshot.correctCount} at ${i}`);
      if(snapshot.selectedCorrect===snapshot.selectedWrong)throw new Error(`selected option classification invalid at ${i}`);
      if(snapshot.selectedCorrect)correctUiChecks++;else wrongUiChecks++;
      if(!snapshot.feedback.trim())throw new Error(`missing feedback at ${i}`);
      if(slug==='visual-change-detection'){
        const feature=snapshot.feedback.includes('الشكل')?'shape':snapshot.feedback.includes('اللون')?'color':'';
        if(feature)visualChangeFeatures.add(feature);
      }
      await page.waitForTimeout(10);
    }
    if(slug==='stroop-advanced'&&stroopRules.size<2)throw new Error(`advanced Stroop did not exercise both rules: ${[...stroopRules]}`);
    if(slug.startsWith('stroop')&&(stroopChecks!==total||stroopInks.size<3||stroopWords.size<3))throw new Error(`insufficient rendered Stroop coverage: checks=${stroopChecks}, inks=${stroopInks.size}, words=${stroopWords.size}`);
    if(slug==='visual-change-detection'&&(visualChangeChecks!==total||visualChangeSizes.size!==5||!visualChangeFeatures.has('shape')||!visualChangeFeatures.has('color')))throw new Error(`insufficient visual-change coverage: checks=${visualChangeChecks}, sizes=${[...visualChangeSizes]}, features=${[...visualChangeFeatures]}`);
    await page.waitForTimeout(30);
    const result=await page.locator('.result-card').innerText();
    if(!result.includes('النتيجة النهائية')||!result.includes(`المحاولات:</strong> ${total}`)&&!result.includes(`المحاولات: ${total}`))throw new Error(`final result incomplete: ${result.slice(0,180)}`);
    if(/IQ|ذكاء سريري|تشخيص/.test(result)&&!result.includes('ليست درجة IQ'))throw new Error('invalid clinical claim');
    await page.reload({waitUntil:'domcontentloaded'});await page.waitForSelector('[data-v12-lab]');
    const saved=await page.locator('.stage-meta span').innerText();if(!saved.includes(`${total} محاولة`))throw new Error(`resume failed: ${saved}`);
    if(slug==='auditory-symbol'){
      const accessiblePrompt=await page.locator('.prompt,.question,[aria-live]').count();
      if(!accessiblePrompt)throw new Error('auditory task has no accessible prompt fallback');
    }
    const allSignals=[...signals.consoleErrors,...signals.pageErrors,...signals.failed];if(allSignals.length)throw new Error(allSignals.join(' | '));
    rows.push({...baseRow,status:'passed',stages,trialsPerStage:per,totalTrials:total,resultChars:result.length,correctUiChecks,wrongUiChecks,stroopChecks,stroopRules:[...stroopRules],stroopInks:stroopInks.size,stroopWords:stroopWords.size,visualChangeChecks,visualChangeSizes:[...visualChangeSizes],visualChangeFeatures:[...visualChangeFeatures],ignoredEnvironmentSignals:signals.ignoredEnvironmentSignals.length});
  }catch(e){errors.push(`${profile}:${route} ${e}`);rows.push({...baseRow,status:'failed',error:String(e)});}finally{await ctx.close();}
}

const browser=await chromium.launch({headless:true,args:['--mute-audio','--autoplay-policy=no-user-gesture-required']});
try{
  for(const profile of ['mobile','desktop']){
    for(const slug of assessments)await runAssessment(browser,slug,profile);
    for(const slug of cognitive)await runCognitive(browser,slug,profile);
  }
}finally{await browser.close();}

const report={version:32,profiles:2,assessmentDefinitions:assessments.length,cognitiveDefinitions:cognitive.length,expectedRuns:(assessments.length+cognitive.length)*2,completedRuns:rows.length,passedRuns:rows.filter(x=>x.status==='passed').length,failedRuns:rows.filter(x=>x.status==='failed').length,errorCount:errors.length,errors,tools:rows};
fs.writeFileSync(path.join(outDir,'all-labs-e2e-v22.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(errors.length)process.exit(1);
