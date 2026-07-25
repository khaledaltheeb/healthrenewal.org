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
assert.equal(report.count, context.window.PA_OPERATIONAL_COUNT, "v221 rights contract must cover the operational professional inventory exactly");
assert.equal(report.allDigitalAdministrationLocked, true);
assert.equal(report.protectedContentStorageAllowed, false);
assert.ok(report.count >= 90, `professional registry unexpectedly small: ${report.count}`);
assert.equal(typeof report.customContractForMode, "function", "mode-bound custom record contract resolver missing");
assert.equal(report.customContractForMode("in_person").recordType, "licensed_professional_administration_record");
assert.equal(report.customContractForMode("remote").recordType, "licensed_professional_administration_record");
assert.equal(report.customContractForMode("external_import").recordType, "external_official_result_record");
assert.equal(report.customContractForMode("record_review").recordType, "external_official_result_record");
assert.ok(!report.customContractForMode("in_person").permittedRightsBases.includes("external_report_only"));
assert.ok(report.customContractForMode("external_import").permittedRightsBases.includes("external_report_only"));

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

const contractSource = fs.readFileSync(path.join(DEMO, "professional-registry-contract-v220.js"), "utf8");
assert.ok(contractSource.includes("customContractForMode"), "custom record mode resolver missing from rights contract");
assert.ok(!contractSource.includes('Object.defineProperty(data.professional, "find"'), "rights contract must not mutate Array.find");

const ui = fs.readFileSync(path.join(DEMO, "professional-registry-maturity-ui-v220.js"), "utf8");
for (const marker of [
  'field("publisher"', 'field("instrumentVersion"', 'field("administrationLanguage"',
  'field("administratorQualification"', 'select("rightsBasis"', 'field("rightsReference"',
  'select("scoreSource"', 'field("officialSourceReference"', 'textarea("selectionRationale"',
  'textarea("administrationQuality"', 'textarea("interpretationLimitations"',
  'textarea("integrationSummary"', 'textarea("recommendations"', 'field("followUpDate"',
  "professional-registry-record-v220", "digitalAdministrationOccurredInsidePlatform: false",
  "protectedContentStored: false", "structured_record_created", "persistAtomically",
  "caseRecord.professionalAssessments.pop()", "if (!persistAtomically(caseRecord, record, now))",
]) {
  assert.ok(ui.includes(marker), `professional UI contract marker missing: ${marker}`);
}
assert.ok(ui.includes('rightsBasis === "pending_review"'), "completed record pending-rights guard missing");
assert.ok(ui.includes("رُفض الحفظ لأن النص قد يتضمن مادة محمية"), "protected-content rejection missing");
assert.ok(!ui.includes("reverse().find"), "legacy record fallback must not be restored");
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(ui), "professional registry UI must remain local-only");

const planning = fs.readFileSync(path.join(DEMO, "professional-registry-planning-compat-v220.js"), "utf8");
for (const marker of [
  "planningDraftAllowed: true", "completedRightsRequired: true", "baseFormValidationPreserved: true",
  "legacyRecordsUpgradable: true", "schemaMigrationAudited: true", "nativeReportValidity",
  'startsWith("maturity_")', "professional-registry-schema-compat-v220.js", "professional-registry-edit-v220.js",
]) {
  assert.ok(planning.includes(marker), `planning and upgrade compatibility marker missing: ${marker}`);
}
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(planning), "planning compatibility must remain local-only");

const schemaCompat = fs.readFileSync(path.join(DEMO, "professional-registry-schema-compat-v220.js"), "utf8");
for (const marker of [
  'canonicalField = "reportIssuedBy"', 'legacyField = "reportIssuer"', "delete record[legacyField]",
  'eventType: "schema_alias_migrated"', "schemaCompatibilityVersion = VERSION",
  "migrationAudited: true", "localOnly: true",
]) {
  assert.ok(schemaCompat.includes(marker), `professional schema compatibility marker missing: ${marker}`);
}
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(schemaCompat), "schema compatibility must remain local-only");

const edit = fs.readFileSync(path.join(DEMO, "professional-registry-edit-v220.js"), "utf8");
for (const marker of [
  "legacyRecordsUpgradable: true", "completedRightsRequired: true", "atomicPersistence: true",
  "structured_record_updated", "contractSnapshot", "customContractForMode", "restore(record, snapshot)",
  "record.professionalMaturity = nextMaturity", "record.digitalAdministrationOccurredInsidePlatform = false",
  "record.protectedContentStored = false",
]) {
  assert.ok(edit.includes(marker), `professional edit-upgrade marker missing: ${marker}`);
}
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(edit), "professional edit upgrade must remain local-only");

const maturityUi = fs.readFileSync(path.join(DEMO, "exploratory-tools-maturity-ui-v220.js"), "utf8");
assert.ok(maturityUi.includes("professional-registry-contract-v220.js"), "professional contract loader missing");
assert.ok(maturityUi.includes("professional-registry-maturity-ui-v220.js"), "professional UI loader missing");

const loader = fs.readFileSync(path.join(DEMO, "institutional-live-v2.js"), "utf8");
assert.ok(loader.includes("professional-registry-planning-compat-v220.js"), "planning compatibility loader missing");

console.log(JSON.stringify({
  status: "passed",
  registryItems: report.count,
  operationalInventoryMatched: true,
  allDigitalAdministrationLocked: report.allDigitalAdministrationLocked,
  protectedContentStorageAllowed: report.protectedContentStorageAllowed,
  structuredRecordSchema: "professional-registry-record-v220",
  planningDraftAllowed: true,
  completedRightsRequired: true,
  legacyRecordsUpgradable: true,
  schemaMigrationAudited: true,
  modeBoundCustomContract: true,
}, null, 2));
