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
assert.equal(report.version, "220.2");
assert.equal(report.count, data.professional.length);
assert.equal(report.allDigitalAdministrationLocked, true);
assert.equal(report.protectedContentStorageAllowed, false);
assert.ok(report.count >= 100, `professional registry unexpectedly small: ${report.count}`);
assert.equal(typeof report.customContractForMode, "function");
assert.equal(report.customContractForMode("in_person").recordType, "licensed_professional_administration_record");
assert.equal(report.customContractForMode("external_import").recordType, "external_official_result_record");
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
  assert.equal(tool.professionalContractVersion, "220.2");
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
assert.ok(!contractSource.includes('Object.defineProperty(data.professional, "find"'), "professional registry must not override Array.find");
assert.ok(contractSource.includes("customContractForMode"), "mode-bound custom contract resolver missing");

const ui = fs.readFileSync(path.join(DEMO, "professional-registry-maturity-ui-v220.js"), "utf8");
for (const marker of [
  "maturity_publisher",
  "maturity_instrumentVersion",
  "maturity_administrationLanguage",
  "maturity_administratorQualification",
  "maturity_rightsBasis",
  "maturity_rightsReference",
  "maturity_scoreSource",
  "maturity_officialSourceReference",
  "maturity_selectionRationale",
  "maturity_administrationQuality",
  "maturity_interpretationLimitations",
  "maturity_integrationSummary",
  "maturity_recommendations",
  "maturity_followUpDate",
  "professional-registry-record-v220",
  "contractSnapshot",
  "custom_mode_bound_contract",
  "saveAtomicProfessionalRecord",
  "set(storeKey(identity.uid), store)",
  "caseRecord.professionalAssessments.pop()",
  "form.dataset.v220Saving",
  "data-v220-record-tool",
  "تسجيل تقرير رسمي",
  "توثيق تطبيق مرخص",
  "digitalAdministrationOccurredInsidePlatform: false",
  "protectedContentStored: false",
  "structured_record_created",
]) {
  assert.ok(ui.includes(marker), `professional UI contract marker missing: ${marker}`);
}
assert.ok(ui.includes('rightsBasis === "pending_review"'), "completed record pending-rights guard missing");
assert.ok(ui.includes("رُفض الحفظ لأن النص قد يتضمن مادة محمية"), "protected-content rejection missing");
for (const forbidden of ["beforeCount", "records.length !== beforeCount + 1", "record.toolId !== toolId", "reverse().find"]) {
  assert.ok(!ui.includes(forbidden), `legacy post-save mutation marker must not return: ${forbidden}`);
}
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(ui), "professional registry UI must remain local-only");

const planning = fs.readFileSync(path.join(DEMO, "professional-registry-planning-compat-v220.js"), "utf8");
for (const marker of [
  "planningDraftAllowed: true",
  "completedRightsRequired: true",
  "protectedContentConfirmationAlwaysRequired: true",
  'requirementOwnership: "professional-registry-maturity-ui-v220"',
  'rights.value = "pending_review"',
  'section.dataset.recordRequirement = completed ? "completed-strict" : "planning-draft"',
  "loadEditorUpgrade",
]) {
  assert.ok(planning.includes(marker), `professional planning compatibility marker missing: ${marker}`);
}
assert.ok(!planning.includes("element.required = false"), "planning compatibility must not clear atomic UI requirements");
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(planning), "planning compatibility must remain local-only");

const edit = fs.readFileSync(path.join(DEMO, "professional-registry-edit-v220.js"), "utf8");
for (const marker of [
  "legacyRecordsUpgradable: true",
  "completedRightsRequired: true",
  "atomicPersistence: true",
  "structured_record_updated",
  "contractSnapshot",
  "customContractForMode",
  "restoreObject",
  "set(storeKey(identity.uid), store)",
  "record.professionalMaturity = nextMaturity",
  "record.digitalAdministrationOccurredInsidePlatform = false",
  "record.protectedContentStored = false",
]) {
  assert.ok(edit.includes(marker), `professional edit-upgrade marker missing: ${marker}`);
}
assert.ok(!edit.includes("registry.customRecordTool"), "edit must resolve custom rights by administration mode");
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(edit), "professional edit upgrade must remain local-only");

const maturityUi = fs.readFileSync(path.join(DEMO, "exploratory-tools-maturity-ui-v220.js"), "utf8");
for (const loader of [
  "professional-registry-contract-v220.js",
  "professional-registry-maturity-ui-v220.js",
  "professional-registry-planning-compat-v220.js",
  "professional-registry-edit-v220.js",
  "professional-registry-report-integration-v220.js",
]) {
  assert.ok(maturityUi.includes(loader), `professional loader missing: ${loader}`);
}
for (const readiness of [
  "PA_PROFESSIONAL_REGISTRY_V220",
  "PA_PROFESSIONAL_RECORD_V220",
  "PA_PROFESSIONAL_PLANNING_COMPAT_V220",
  "PA_PROFESSIONAL_EDIT_V220",
  "PA_PROFESSIONAL_REPORT_V220",
]) {
  assert.ok(maturityUi.includes(readiness), `readiness contract missing: ${readiness}`);
}
assert.ok(maturityUi.includes("const ensureScriptReady"), "readiness-aware script loader missing");
assert.ok(maturityUi.includes("onReady: loadProfessionalUi"), "professional UI must follow rights contract");
assert.ok(maturityUi.includes("onReady: loadPlanningCompatibility"), "planning compatibility must follow professional UI");
assert.ok(maturityUi.includes("onReady: loadEditIntegration"), "edit upgrade must follow planning compatibility");
assert.ok(maturityUi.includes("onReady: loadReportIntegration"), "report integration must follow edit upgrade");
assert.ok(maturityUi.includes("draft records remain in stricter fallback mode"), "planning load failure must be explicit and fail to stricter mode");
assert.ok(maturityUi.includes("legacy-record upgrade UI remains unavailable"), "edit load failure must be explicit");

console.log(JSON.stringify({
  status: "passed",
  registryItems: report.count,
  allDigitalAdministrationLocked: report.allDigitalAdministrationLocked,
  protectedContentStorageAllowed: report.protectedContentStorageAllowed,
  structuredRecordSchema: "professional-registry-record-v220",
  atomicRecordPersistence: true,
  atomicEditPersistence: true,
  modeBoundCustomContract: true,
  safeRecordButtons: true,
  readinessAwareLoader: true,
  reportIntegrationAfterEditUpgrade: true,
}, null, 2));