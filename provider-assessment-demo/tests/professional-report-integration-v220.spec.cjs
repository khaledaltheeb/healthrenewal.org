"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..", "..");
const DEMO = path.join(ROOT, "provider-assessment-demo");
const report = fs.readFileSync(path.join(DEMO, "professional-registry-report-integration-v220.js"), "utf8");
const loader = fs.readFileSync(path.join(DEMO, "exploratory-tools-maturity-ui-v220.js"), "utf8");

for (const marker of [
  "case-report-professional-sources-v220",
  "professionalSourcesContract",
  "reportMaturityVersion",
  "professional_sources_snapshot_attached",
  "rightsValidCompletedRecords",
  "incompleteCompletedRecordIds",
  "protectedContentStored: false",
  'reviewStatus?.value === "final"',
  "لا يمكن اعتماد التقرير نهائيًا",
  "reports.length !== beforeCount + 1",
  "professional-maturity-report-table",
  "تفاصيل التطبيقات المهنية والحقوق",
]) {
  assert.ok(report.includes(marker), `professional report contract marker missing: ${marker}`);
}

for (const requirement of [
  "value.instrument?.publisher",
  "value.instrument?.version",
  "value.instrument?.language",
  "value.administrator?.qualification",
  "value.rights?.basis",
  "value.rights?.reference",
  "value.officialResultSource?.type",
  "value.officialResultSource?.reference",
  "value.selectionRationale",
  "value.administrationQuality",
  "value.interpretationLimitations",
  "value.integrationSummary",
  "value.recommendations",
  "value.followUpDate",
]) {
  assert.ok(report.includes(requirement), `final report validity requirement missing: ${requirement}`);
}

assert.ok(report.includes("itemResponsesStored === false"), "item response exclusion is not verified");
assert.ok(report.includes("scoringKeyStored === false"), "scoring key exclusion is not verified");
assert.ok(report.includes("normTablesStored === false"), "norm table exclusion is not verified");
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource/.test(report), "professional report integration must remain local-only");
assert.ok(loader.includes("professional-registry-report-integration-v220.js"), "report integration loader missing");
assert.ok(loader.includes('document.getElementById("case-report-form")'), "report-form readiness guard missing");
assert.ok(loader.includes("attempt < 100"), "bounded report loader wait missing");

console.log(JSON.stringify({
  status: "passed",
  finalReportGuard: true,
  structuredProfessionalSourceSnapshot: true,
  protectedContentStored: false,
  localOnly: true,
}, null, 2));
