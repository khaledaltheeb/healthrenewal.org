"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..", "..");
const DEMO = path.join(ROOT, "provider-assessment-demo");
const context = vm.createContext({ window: {} });

for (const file of ["catalog.js", "catalog-extra.js", "explorer-saturation-v1.js"]) {
  const source = fs.readFileSync(path.join(DEMO, file), "utf8");
  new vm.Script(source, { filename: file }).runInContext(context);
}

const data = context.window.PA_DEMO_DATA;
const contract = context.window.PA_EXPLORER_SATURATION;
assert.ok(data, "PA_DEMO_DATA must be available");
assert.ok(contract, "PA_EXPLORER_SATURATION must be published");
assert.equal(contract.schema, "pa-explorer-saturation-v1");
assert.equal(contract.toolCount, 20);
assert.equal(data.explorers.length, 20);
assert.ok(contract.requiredCapabilities.length >= 12);

const expectedTools = new Set([
  "development-overview",
  "communication-participation",
  "attention-executive",
  "learning-access",
  "adaptive-daily-living",
  "sensory-regulation",
  "motor-participation",
  "emotional-regulation",
  "social-participation",
  "play-flexibility",
  "sleep-routine",
  "feeding-participation",
  "school-participation",
  "self-advocacy",
  "caregiver-priorities",
  "behavior-context-observation",
  "fine-motor-access",
  "planning-working-memory",
  "wellbeing-participation",
  "transition-adult-life"
]);
assert.deepEqual(new Set(data.explorers.map((tool) => tool.id)), expectedTools);

const globalQuestionIds = new Set();
const officialHosts = new Set(["www.who.int", "www.cdc.gov", "www.aap.org", "sites.ed.gov"]);
let totalQuestions = 0;
let totalSafetyStops = 0;

for (const tool of data.explorers) {
  const profile = tool.institutionalProfile;
  assert.ok(profile, `${tool.id}: institutional profile is required`);
  assert.equal(profile.schema, "pa-explorer-saturation-v1");
  assert.equal(profile.minimumQuestionCount, 14);
  assert.equal(profile.professionalRecordLinkage, true);
  assert.equal(profile.longitudinalComparabilityRequired, true);
  assert.match(profile.interpretationBoundary, /non-diagnostic/);

  assert.ok(tool.questions.length >= 14, `${tool.id}: at least 14 questions are required`);
  assert.ok(tool.guide.length >= 8, `${tool.id}: expanded application guidance is required`);
  assert.ok(profile.domains.length >= 6, `${tool.id}: multi-domain coverage is required`);
  assert.ok(profile.respondents.length >= 3, `${tool.id}: multi-informant coverage is required`);
  assert.ok(profile.environments.length >= 3, `${tool.id}: multi-setting coverage is required`);
  assert.ok(profile.confounders.length >= 4, `${tool.id}: confounder review is required`);
  assert.ok(profile.supports.length >= 4, `${tool.id}: accommodation options are required`);
  assert.ok(profile.reportOutputs.length >= 6, `${tool.id}: professional report outputs are required`);
  assert.ok(profile.followUpRules.length >= 3, `${tool.id}: follow-up rules are required`);
  assert.ok(profile.frameworks.length >= 4, `${tool.id}: official framework references are required`);

  const localIds = new Set();
  const safetyQuestions = tool.questions.filter((question) => question.safety === true);
  assert.equal(safetyQuestions.length, 1, `${tool.id}: exactly one explicit safety stop is required`);
  totalSafetyStops += safetyQuestions.length;

  const requiredDomains = new Set(tool.questions.map((question) => question.domain));
  for (const domain of ["مصدر المعلومات", "الفترة الزمنية", "السياق", "التكييفات", "نقاط القوة", "جودة البيانات"]) {
    assert.ok(requiredDomains.has(domain), `${tool.id}: missing contextual domain ${domain}`);
  }

  for (const question of tool.questions) {
    assert.ok(question.id && question.text && question.domain && question.type, `${tool.id}: malformed question`);
    assert.ok(!localIds.has(question.id), `${tool.id}: duplicate local question id ${question.id}`);
    assert.ok(!globalQuestionIds.has(question.id), `duplicate global question id ${question.id}`);
    localIds.add(question.id);
    globalQuestionIds.add(question.id);
  }

  for (const framework of profile.frameworks) {
    const url = new URL(framework.url);
    assert.equal(url.protocol, "https:", `${tool.id}: framework URL must use HTTPS`);
    assert.ok(officialHosts.has(url.hostname), `${tool.id}: unofficial framework host ${url.hostname}`);
  }

  totalQuestions += tool.questions.length;
}

assert.equal(totalQuestions, 280, "The first saturation release must provide exactly 280 structured questions");
assert.equal(totalSafetyStops, 20, "Every tool must have one explicit safety stop");
assert.equal(globalQuestionIds.size, totalQuestions, "All question identifiers must be globally unique");

const source = fs.readFileSync(path.join(DEMO, "explorer-saturation-v1.js"), "utf8");
for (const forbidden of [
  "diagnosisScore",
  "diagnosticConclusion",
  "eligibilityDecision",
  "normTable",
  "answerKey",
  "cutoffDiagnosis"
]) {
  assert.ok(!source.includes(forbidden), `forbidden automated or protected construct: ${forbidden}`);
}

console.log(JSON.stringify({
  schema: contract.schema,
  tools: data.explorers.length,
  questions: totalQuestions,
  safetyStops: totalSafetyStops,
  globallyUniqueQuestionIds: globalQuestionIds.size,
  officialFrameworks: contract.frameworks.length,
  status: "passed"
}, null, 2));
