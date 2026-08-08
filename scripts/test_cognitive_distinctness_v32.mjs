import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { performance } from 'node:perf_hooks';

const root = process.argv[2] || process.env.AUDIT_SITE_ROOT || '_site';
const outDir = process.env.AUDIT_OUT_DIR || path.join(root, 'api');
fs.mkdirSync(outDir, { recursive: true });

const runtime = fs.readFileSync(path.join(root, 'assets/js/lab-v12.js'), 'utf8');
const context = { console, performance, setTimeout, clearTimeout, globalThis: null, Date, Math };
context.globalThis = context;
vm.createContext(context);
vm.runInContext(runtime, context, { filename: 'lab-v12.js' });
const api = context.__PTERMINOLOGY_LAB_V202__;
if (!api?.makeTrial || !api?.isCorrect) throw new Error('cognitive runtime API missing');

function value(item) {
  return String(typeof item === 'object' && item !== null ? item.value : item);
}
function definitionFor(slug) {
  const file = path.join(root, 'cognitive-lab', slug, 'index.html');
  const source = fs.readFileSync(file, 'utf8');
  const match = source.match(/<script type="application\/json" id="lab-definition">(.*?)<\/script>/s);
  if (!match) throw new Error(`${slug}: missing definition`);
  return JSON.parse(match[1].replaceAll('<\\/', '</'));
}
function signature(trial) {
  return JSON.stringify([
    trial.study || '',
    trial.prompt || '',
    trial.answer,
    (trial.options || []).map(value),
    trial.kind || '',
    trial.spanLength || 0,
    trial.visualSearchSetSize || 0,
    trial.sustainedTarget || '',
    trial.attentionRule || '',
  ]);
}

const dirs = fs.readdirSync(path.join(root, 'cognitive-lab'), { withFileTypes: true })
  .filter(entry => entry.isDirectory())
  .map(entry => entry.name)
  .sort();
const errors = [];
const rows = [];
const fingerprints = new Map();
const binaryModes = new Set([
  'go_no_go',
  'one_back',
  'response_inhibition',
  'sustained_attention',
  'symbol_memory',
  'symbol_search',
  'two_back',
  'three_back',
]);
const specializedSlugs = new Set([
  'attention-switch',
  'choice-reaction',
  'digit-span-backward',
  'digit-span-forward',
  'letter-span',
  'semantic-fluency',
  'simple-reaction',
  'spatial-span',
  'sustained-attention',
  'visual-reaction',
  'visual-search',
  'word-categories',
]);

if (dirs.length !== 53) errors.push(`expected 53 cognitive tools, found ${dirs.length}`);

let checkedTrials = 0;
for (const slug of dirs) {
  const definition = definitionFor(slug);
  if (specializedSlugs.has(slug) && definition.distinctness_version !== 32) {
    errors.push(`${slug}: distinctness_version=${definition.distinctness_version}`);
  }
  const routeSignatures = [];
  let minimumOptions = Infinity;
  let maximumOptions = 0;
  for (let stage = 0; stage < 5; stage += 1) {
    for (const seed of [17, 43, 89, 137, 211]) {
      for (let index = 0; index < 12; index += 1) {
        let trial;
        try {
          trial = api.makeTrial(definition, stage, index, seed);
        } catch (error) {
          errors.push(`${slug} s${stage} seed${seed} i${index}: generator threw ${error.message}`);
          continue;
        }
        checkedTrials += 1;
        const values = (trial.options || []).map(value);
        minimumOptions = Math.min(minimumOptions, values.length);
        maximumOptions = Math.max(maximumOptions, values.length);
        const joined = [
          trial.study || '',
          trial.prompt || '',
          trial.answer,
          trial.explanation || '',
          ...values,
        ].join('|');
        if (/undefined|NaN|null/.test(joined)) errors.push(`${slug} s${stage} i${index}: invalid generated value`);
        if (new Set(values).size !== values.length) errors.push(`${slug} s${stage} i${index}: duplicate options`);
        if (values.filter(item => item === String(trial.answer)).length !== 1) {
          errors.push(`${slug} s${stage} i${index}: answer not exactly once`);
        }
        if (!api.isCorrect(trial, trial.answer)) errors.push(`${slug} s${stage} i${index}: correct answer rejected`);
        for (const wrong of values.filter(item => item !== String(trial.answer))) {
          if (api.isCorrect(trial, wrong)) errors.push(`${slug} s${stage} i${index}: wrong answer accepted`);
        }
        if (!trial.prompt || !trial.explanation) errors.push(`${slug} s${stage} i${index}: missing prompt or explanation`);
        if (slug === 'simple-reaction') {
          if (values.length !== 1 || values[0] !== 'اضغط الآن' || trial.answer !== 'اضغط الآن') {
            errors.push(`${slug} s${stage} i${index}: must have exactly one response`);
          }
          if (trial.kind !== 'reaction') errors.push(`${slug}: wrong kind`);
          if (!(trial.delay >= trial.reactionForeperiodMin && trial.delay <= trial.reactionForeperiodMax)) {
            errors.push(`${slug} s${stage} i${index}: delay outside declared range`);
          }
        } else if (binaryModes.has(definition.mode)) {
          if (values.length !== 2) errors.push(`${slug} s${stage} i${index}: expected binary choices`);
        } else if (values.length < 4) {
          errors.push(`${slug} s${stage} i${index}: expected at least four choices`);
        }
        routeSignatures.push(signature(trial));
      }
    }
  }
  fingerprints.set(slug, JSON.stringify(routeSignatures));
  rows.push({
    slug,
    mode: definition.mode,
    minimumOptions: Number.isFinite(minimumOptions) ? minimumOptions : 0,
    maximumOptions,
    generatedTrials: routeSignatures.length,
    uniqueSignatures: new Set(routeSignatures).size,
  });
}

const exactDuplicateRoutes = [];
for (let first = 0; first < dirs.length; first += 1) {
  for (let second = first + 1; second < dirs.length; second += 1) {
    if (fingerprints.get(dirs[first]) === fingerprints.get(dirs[second])) {
      exactDuplicateRoutes.push([dirs[first], dirs[second]]);
    }
  }
}
if (exactDuplicateRoutes.length) errors.push(`exact duplicate routes: ${JSON.stringify(exactDuplicateRoutes)}`);

const simple = definitionFor('simple-reaction');
for (let stage = 0; stage < 5; stage += 1) {
  const trial = api.makeTrial(simple, stage, 4, 900 + stage);
  const expectedMin = Math.max(250, 600 - stage * 50);
  const expectedMax = 1100 + stage * 180;
  if (trial.reactionForeperiodMin !== expectedMin || trial.reactionForeperiodMax !== expectedMax) {
    errors.push(`simple-reaction stage ${stage}: incorrect foreperiod ${trial.reactionForeperiodMin}-${trial.reactionForeperiodMax}`);
  }
}

const choice = definitionFor('choice-reaction');
const visualReaction = definitionFor('visual-reaction');
for (let stage = 0; stage < 5; stage += 1) {
  const choiceTrial = api.makeTrial(choice, stage, 2, 1200 + stage);
  const visualTrial = api.makeTrial(visualReaction, stage, 2, 1200 + stage);
  if (choiceTrial.choiceReactionMapping !== 'arrow-direction' || !choiceTrial.prompt.includes('اتجاه السهم')) {
    errors.push(`choice-reaction stage ${stage}: mapping contract missing`);
  }
  if (!Number.isFinite(visualTrial.visualReactionTargetSize) || !visualTrial.prompt.includes('grid-template-columns')) {
    errors.push(`visual-reaction stage ${stage}: grid contract missing`);
  }
  if (choiceTrial.prompt === visualTrial.prompt) errors.push(`reaction routes identical at stage ${stage}`);
}

const sustained = definitionFor('sustained-attention');
const expectedCycles = [2, 3, 4, 5, 6];
for (let stage = 0; stage < 5; stage += 1) {
  const trials = Array.from({ length: 24 }, (_, index) => api.makeTrial(sustained, stage, index, 1500));
  if (new Set(trials.map(trial => trial.sustainedTarget)).size !== 1) {
    errors.push(`sustained-attention stage ${stage}: target changes within stage`);
  }
  if (!trials.every(trial => trial.targetCycle === expectedCycles[stage])) {
    errors.push(`sustained-attention stage ${stage}: target cycle mismatch`);
  }
  if (!trials.some(trial => trial.targetPresent) || !trials.some(trial => !trial.targetPresent)) {
    errors.push(`sustained-attention stage ${stage}: missing targets or distractors`);
  }
}

const visualSearch = definitionFor('visual-search');
const expectedSizes = [12, 18, 24, 30, 36];
for (let stage = 0; stage < 5; stage += 1) {
  const trial = api.makeTrial(visualSearch, stage, 6, 1800 + stage);
  if (trial.visualSearchSetSize !== expectedSizes[stage]) {
    errors.push(`visual-search stage ${stage}: set size=${trial.visualSearchSetSize}`);
  }
  const expectedSimilarity = stage < 2 ? 'منخفض' : 'مرتفع';
  if (trial.visualSearchSimilarity !== expectedSimilarity) {
    errors.push(`visual-search stage ${stage}: similarity=${trial.visualSearchSimilarity}`);
  }
  const row = trial.prompt.split('؟').slice(1).join('؟');
  const occurrences = [...row].filter(character => character === String(trial.answer)).length;
  if (occurrences !== 1) errors.push(`visual-search stage ${stage}: target occurrences=${occurrences}`);
}

const categories = definitionFor('word-categories');
const semantic = definitionFor('semantic-fluency');
for (let stage = 0; stage < 5; stage += 1) {
  const categoryTrial = api.makeTrial(categories, stage, 5, 2200 + stage);
  const semanticTrial = api.makeTrial(semantic, stage, 5, 2200 + stage);
  if (!categoryTrial.prompt.includes('الفئة الأدق') || categoryTrial.categoryMemberCount !== Math.min(6, 2 + stage)) {
    errors.push(`word-categories stage ${stage}: category contract missing`);
  }
  if (!semanticTrial.guidedSemanticRetrieval || !semanticTrial.prompt.includes('استرجاع دلالي موجّه')) {
    errors.push(`semantic-fluency stage ${stage}: guided retrieval contract missing`);
  }
  if (categoryTrial.prompt === semanticTrial.prompt) errors.push(`semantic tasks identical at stage ${stage}`);
}

const switchDefinition = definitionFor('attention-switch');
const expectedSwitchCounts = [0, 3, 4, 9];
for (let stage = 0; stage < 4; stage += 1) {
  const trials = Array.from({ length: 10 }, (_, index) => api.makeTrial(switchDefinition, stage, index, 2600));
  const switches = trials.filter(trial => trial.switchTrial).length;
  if (switches !== expectedSwitchCounts[stage]) {
    errors.push(`attention-switch stage ${stage}: switches=${switches}`);
  }
  if (!trials.every(trial => ['color', 'shape'].includes(trial.attentionRule))) {
    errors.push(`attention-switch stage ${stage}: missing rule metadata`);
  }
}
const unpredictable = Array.from({ length: 30 }, (_, index) => api.makeTrial(switchDefinition, 4, index, 2600));
const unpredictableSwitches = unpredictable.filter(trial => trial.switchTrial).length;
if (unpredictableSwitches < 4 || unpredictableSwitches > 25) {
  errors.push(`attention-switch stage 4: implausible switches=${unpredictableSwitches}`);
}

for (const slug of ['digit-span-forward', 'digit-span-backward', 'letter-span', 'spatial-span']) {
  const definition = definitionFor(slug);
  for (let stage = 0; stage < 5; stage += 1) {
    for (let index = 0; index < 20; index += 1) {
      const trial = api.makeTrial(definition, stage, index, 3100 + index);
      const values = trial.options.map(value);
      if (trial.spanLength !== 3 + stage) errors.push(`${slug} stage ${stage}: spanLength=${trial.spanLength}`);
      if (trial.uniqueStudyTokens !== trial.spanLength) errors.push(`${slug} stage ${stage}: repeated study tokens`);
      if (!trial.study || trial.prompt.includes(trial.answer)) errors.push(`${slug} stage ${stage}: study not hidden`);
      if (values.length !== 4 || new Set(values).size !== 4) errors.push(`${slug} stage ${stage}: options=${values.length}/${new Set(values).size}`);
      if (!values.includes(String(trial.answer))) errors.push(`${slug} stage ${stage}: answer missing`);
      if (!(trial.studyMs >= 1900 && trial.studyMs <= 3400)) errors.push(`${slug} stage ${stage}: studyMs=${trial.studyMs}`);
    }
  }
}

const report = {
  version: 32,
  status: errors.length ? 'failed' : 'passed',
  tools: dirs.length,
  specializedRoutes: specializedSlugs.size,
  checkedTrials,
  exactDuplicateRouteCount: exactDuplicateRoutes.length,
  exactDuplicateRoutes,
  errors,
  rows,
};
fs.writeFileSync(path.join(outDir, 'cognitive-distinctness-test-v32.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
