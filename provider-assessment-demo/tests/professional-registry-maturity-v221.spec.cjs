"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..", "..");
const DEMO = path.join(ROOT, "provider-assessment-demo");
const context = { window: {}, console };
context.window.window = context.window;
vm.createContext(context);

for (const file of [
  "catalog.js",
  "professional-master-registry.js",
  "catalog-operational-v2.js",
  "professional-registry-contract-v220.js",
]) {
  vm.runInContext(fs.readFileSync(path.join(DEMO, file), "utf8"), context, { filename: file });
}

const data = context.window.PA_DEMO_DATA;
const report = context.window.PA_PROFESSIONAL_REGISTRY_V220;
assert.ok(data?.professional?.length, "professional registry did not load");
assert.ok(report, "professional v220 report did not load");
assert.equal(report.version, "220.1");
assert.equal(report.count, data.professional.length);
assert.equal(report.allDigitalAdministrationLocked, true);
assert.equal(report.protectedContentStorageAllowed, false);
assert.ok(report.count >= 100, `professional registry unexpectedly small: ${report.count}`);

const ids = new Set();
const requiredCompleted = [
  "publisher", "instrumentVersion", "administrationLanguage", "administratorQualification",
  "rightsBasis", "rightsReference", "scoreSource", "officialSourceReference",
  "selectionRationale", "administrationQuality", "interpretationLimitations",
  "integrationSummary", "recommendations", "followUpDate",
];

for (const tool of data.professional) {
  assert.ok(tool.id && !ids.has(tool.id), `missing or duplicate tool id: ${tool.id}`);
  ids.add(tool.id);
  const contract = tool.professionalContract;
  assert.ok(contract, `${tool.id}: contract missing`);
  assert.equal(tool.professionalContractVersion, "220.1");
  assert.equal(tool.digitalAdministrationStatus, "not_available_in_platform");
  assert.equal(tool.resultRecordingStatus, "available_without_protected_materials");
  assert.equal(contract.officialAdministrationInsidePlatform, false);
  assert.equal(contract.resultRecordingAllowed, true);
  assert.equal(contract.protectedContentStorageAllowed, false);
  assert.equal(contract.itemResponsesStorageAllowed, false);
  assert.equal(contract.scoringKeyStorageAllowed, false);
  assert.equal(contract.normTableStorageAllowed, false);
  assert.equal(contract.sourceDocumentRequiredForCompletedRecord, true);
  assert.equal(contract.publisherVersionLanguageRequired, true);
  assert.equal(contract.qualificationRequired, true);
  assert.ok(Array.isArray(contract.recommendedRoles) && contract.recommendedRoles.length >= 1, `${tool.id}: roles missing`);
  assert.ok(Array.isArray(contract.permittedScoreSources) && contract.permittedScoreSources.length === 4, `${tool.id}: score sources incomplete`);
  assert.deepEqual([...contract.requiredCompletedFields], requiredCompleted, `${tool.id}: completed record contract drifted`);
  assert.ok(!contract.permittedRightsBases.includes("pending_review"), `${tool.id}: pending rights cannot authorize completion`);
  if (contract.recordType === "external_official_result_record") {
    assert.ok(contract.permittedRightsBases.includes("external_report_only"), `${tool.id}: external report basis missing`);
  } else {
    assert.ok(!contract.permittedRightsBases.includes("external_report_only"), `${tool.id}: non-external tool accepts external-only basis`);
  }
  assert.ok(contract.interpretationLimits.some((text) => text.includes("لا تفسر النتيجة منفردة")), `${tool.id}: non-diagnostic limit missing`);
}

const ui = fs.readFileSync(path.join(DEMO, "professional-registry-maturity-ui-v220.js"), "utf8");
for (const marker of [
  'field("publisher"',
  'field("instrumentVersion"',
  'field("administrationLanguage"',
  'field("administratorQualification"',
  'select("rightsBasis"',
  'field("rightsReference"',
  'select("scoreSource"',
  'field("officialSourceReference"',
  'textarea("selectionRationale"',
  'textarea("administrationQuality"',
  'textarea("interpretationLimitations"',
  'textarea("integrationSummary"',
  'textarea("recommendations"',
  'field("followUpDate"',
  "professional-registry-record-v220",
  "digitalAdministrationOccurredInsidePlatform: false",
  "protectedContentStored: false",
  "structured_record_created",
  "persistAtomically",
  "caseRecord.professionalAssessments.pop()",
  "if (!persistAtomically(caseRecord, record, now))",
]) {
  assert.ok(ui.includes(marker), `professional UI contract marker missing: ${marker}`);
}
assert.ok(ui.includes('rightsBasis === "pending_review"'), "completed record pending-rights guard missing");
assert.ok(ui.includes("رُفض الحفظ لأن النص قد يتضمن مادة محمية"), "protected-content rejection missing");
assert.ok(!ui.includes("reverse().find"), "legacy record fallback must not be restored");
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(ui), "professional registry UI must remain local-only");

const maturityUi = fs.readFileSync(path.join(DEMO, "exploratory-tools-maturity-ui-v220.js"), "utf8");
assert.ok(maturityUi.includes("professional-registry-contract-v220.js"), "professional contract loader missing");
assert.ok(maturityUi.includes("professional-registry-maturity-ui-v220.js"), "professional UI loader missing");

const loader = fs.readFileSync(path.join(DEMO, "institutional-live-v2.js"), "utf8");
assert.ok(loader.includes("professional-registry-planning-compat-v220.js"), "planning compatibility loader missing");

const compatibility = fs.readFileSync(path.join(DEMO, "professional-registry-planning-compat-v220.js"), "utf8");
assert.ok(compatibility.includes("planningDraftAllowed: true"), "planning draft compatibility missing");
assert.ok(compatibility.includes("completedRightsRequired: true"), "completed rights requirement missing");
assert.ok(compatibility.includes("nativeReportValidity"), "planning compatibility must preserve base form validation");
assert.ok(compatibility.includes('startsWith("maturity_")'), "planning compatibility must relax only maturity fields");

console.log(JSON.stringify({
  status: "passed",
  registryItems: report.count,
  allDigitalAdministrationLocked: report.allDigitalAdministrationLocked,
  protectedContentStorageAllowed: report.protectedContentStorageAllowed,
  structuredRecordSchema: "professional-registry-record-v220",
  planningDraftAllowed: true,
  completedRightsRequired: true,
}, null, 2));
