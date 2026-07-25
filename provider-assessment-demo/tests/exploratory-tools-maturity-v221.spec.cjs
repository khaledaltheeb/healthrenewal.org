"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..", "..");
const DEMO = path.join(ROOT, "provider-assessment-demo");
const FILES = [
  "catalog.js",
  "catalog-extra.js",
  "exploratory-tools-maturity-runtime-v220.js",
  "exploratory-tools-maturity-specs-1-v220.js",
  "exploratory-tools-maturity-specs-2-v220.js",
  "exploratory-tools-maturity-specs-3-v220.js",
  "exploratory-tools-maturity-specs-4-v220.js",
  "exploratory-tools-maturity-finalize-v220.js",
];

const context = { window: {}, console };
context.window.window = context.window;
vm.createContext(context);
for (const file of FILES) {
  const source = fs.readFileSync(path.join(DEMO, file), "utf8");
  vm.runInContext(source, context, { filename: file });
}

const data = context.window.PA_DEMO_DATA;
const report = context.window.PA_EXPLORATORY_MATURITY_V220;
assert.ok(data, "assessment catalog did not load");
assert.ok(report, "v220 maturity report did not load");
assert.equal(data.explorers.length, 20, "exactly twenty exploratory tools are required");
assert.equal(report.toolCount, 20);
assert.equal(report.nonDiagnostic, true);
assert.equal(report.protectedItemsCopied, false);
assert.ok(report.minimumQuestions >= 12, `minimum questions fell to ${report.minimumQuestions}`);
assert.ok(report.minimumDomains >= 6, `minimum domains fell to ${report.minimumDomains}`);

const allToolIds = new Set(data.explorers.map((tool) => tool.id));
const questionIds = new Set();
const safetyRequired = new Set([
  "development-overview",
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
  "transition-adult-life",
]);
const protectedNames = /ADOS|ADI-R|Vineland|ABAS|WISC|WPPSI|WAIS|Conners|BRIEF|WIAT|CELF|Bayley|Sensory Profile|BASC|CBCL|M-CHAT|Vanderbilt|SNAP-IV/i;
const diagnosticClaims = /(يشخ[ّ]?ص|يثبت التشخيص|درجة معيارية|نسبة مئينية|معيار عمري)/;

for (const tool of data.explorers) {
  assert.equal(tool.questionSetVersion, "220.1", `${tool.id}: version missing`);
  assert.equal(tool.maturityStatus, "expanded_original_exploratory", `${tool.id}: maturity status missing`);
  assert.ok(tool.questions.length >= 12, `${tool.id}: fewer than 12 questions`);

  const domains = new Set(tool.questions.map((question) => question.domain).filter(Boolean));
  assert.ok(domains.size >= 6, `${tool.id}: fewer than 6 domains`);
  assert.ok(tool.questions.some((question) => question.type === "textarea"), `${tool.id}: contextual narrative item missing`);
  if (safetyRequired.has(tool.id)) {
    assert.ok(tool.questions.some((question) => question.safety), `${tool.id}: safety item missing`);
  }

  const protocol = tool.protocol;
  assert.ok(protocol, `${tool.id}: protocol missing`);
  assert.equal(protocol.instrumentType, "original_exploratory_non_diagnostic");
  assert.equal(protocol.rightsStatus, "original_platform_content");
  for (const field of ["purpose", "referralQuestion", "observationWindow", "followUp", "alignmentNotice"]) {
    assert.ok(String(protocol[field] || "").length >= 20, `${tool.id}: weak protocol field ${field}`);
  }
  for (const field of ["respondents", "contexts", "useWhen", "doNotUseWhen", "interpretationLimits", "references"]) {
    assert.ok(Array.isArray(protocol[field]) && protocol[field].length >= 2, `${tool.id}: incomplete ${field}`);
  }
  for (const reference of protocol.references) {
    assert.match(reference.url, /^https:\/\//, `${tool.id}: reference must be HTTPS`);
  }
  assert.equal(protocol.minimumEvidence.unknownResponseReviewRequired, true);
  assert.equal(protocol.minimumEvidence.urgentSafetyOverridesScoring, true);

  for (const next of tool.next || []) {
    assert.ok(allToolIds.has(next), `${tool.id}: unresolved next tool ${next}`);
  }

  for (const question of tool.questions) {
    assert.ok(question.id, `${tool.id}: question id missing`);
    assert.ok(!questionIds.has(question.id), `duplicate question id ${question.id}`);
    questionIds.add(question.id);
    assert.ok(question.domain, `${question.id}: domain missing`);
    assert.ok(String(question.text || "").length >= 12, `${question.id}: question text too short`);
    assert.doesNotMatch(question.text, protectedNames, `${question.id}: protected instrument name leaked into original item`);
    assert.doesNotMatch(question.text, diagnosticClaims, `${question.id}: diagnostic or normative claim found`);
    if (question.type !== "textarea") {
      assert.ok(Array.isArray(question.options) && question.options.length >= 3, `${question.id}: options missing`);
      if (!question.safety && question.maturityVersion === "220.1") {
        assert.ok(question.options.some((option) => option[0] === "unknown"), `${question.id}: unknown option missing`);
      }
    }
  }
}

const loader = fs.readFileSync(path.join(DEMO, "institutional-live-v2.js"), "utf8");
for (const file of FILES.slice(2)) {
  assert.ok(loader.includes(file), `institutional loader does not include ${file}`);
}
assert.ok(loader.includes("exploratory-tools-maturity-ui-v220.js"), "maturity UI loader missing");
assert.ok(loader.includes("professional-registry-planning-compat-v220.js"), "planning compatibility loader missing");
assert.ok(loader.includes('const RELEASE = "2026.07.24-live.7"'), "runtime release must remain synchronized with index and service worker");
assert.ok(!loader.includes("2026.07.25-live.8"), "unsynchronized live.8 release must not be introduced");

console.log(JSON.stringify({
  status: "passed",
  tools: data.explorers.length,
  questions: questionIds.size,
  minimumQuestions: report.minimumQuestions,
  minimumDomains: report.minimumDomains,
  safetyTools: safetyRequired.size,
  nonDiagnostic: report.nonDiagnostic,
  protectedItemsCopied: report.protectedItemsCopied,
  liveRelease: "2026.07.24-live.7",
}, null, 2));
