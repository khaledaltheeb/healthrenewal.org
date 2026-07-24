"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..", "..");
const DEMO = path.join(ROOT, "provider-assessment-demo");
const listeners = new Map();
const documentElement = { dataset: {} };
const documentStub = {
  documentElement,
  addEventListener(type, handler) {
    if (!listeners.has(type)) listeners.set(type, []);
    listeners.get(type).push(handler);
  },
  getElementById() { return null; },
};
const storage = new Map();
const localStorageStub = {
  getItem(key) { return storage.has(key) ? storage.get(key) : null; },
  setItem(key, value) { storage.set(key, String(value)); },
};
class HTMLFormElementStub {}
class CustomEventStub {
  constructor(type, options = {}) { this.type = type; this.detail = options.detail; }
}

const context = vm.createContext({
  window: {
    addEventListener() {},
    dispatchEvent() {},
  },
  document: documentStub,
  localStorage: localStorageStub,
  HTMLFormElement: HTMLFormElementStub,
  CustomEvent: CustomEventStub,
  CSS: { escape: (value) => String(value) },
  FormData: class {},
  Blob: class {},
  URL,
  setTimeout() {},
  queueMicrotask() {},
  console,
});

for (const file of [
  "catalog.js",
  "catalog-extra.js",
  "explorer-saturation-v1.js",
  "explorer-saturation-record-v1.js",
]) {
  const source = fs.readFileSync(path.join(DEMO, file), "utf8");
  new vm.Script(source, { filename: file }).runInContext(context);
}

const api = context.window.PA_EXPLORER_SATURATION_RECORD;
const tools = context.window.PA_DEMO_DATA.explorers;
assert.ok(api, "professional-record bridge API must be exposed");
assert.equal(api.schema, "pa-explorer-saturation-record-v1");
assert.equal(documentElement.dataset.explorerSaturationRecord, api.release);
assert.ok(listeners.has("submit"), "the bridge must capture assessment submissions");
assert.ok(listeners.has("click"), "the bridge must enhance tool guidance");

for (const tool of tools) {
  const snapshot = api.snapshotProfile(tool);
  assert.equal(snapshot.schema, "pa-explorer-saturation-v1");
  assert.equal(snapshot.toolId, tool.id);
  assert.equal(snapshot.professionalRecordLinkage, true);
  assert.equal(snapshot.longitudinalComparabilityRequired, true);
  assert.ok(snapshot.domains.length >= 6);
  assert.ok(snapshot.respondents.length >= 3);
  assert.ok(snapshot.environments.length >= 3);
  assert.ok(snapshot.confounders.length >= 4);
  assert.ok(snapshot.supports.length >= 4);
  assert.ok(snapshot.reportOutputs.length >= 6);
  assert.ok(snapshot.followUpRules.length >= 3);
  assert.ok(snapshot.frameworkIds.length >= 4);
  assert.match(snapshot.interpretationBoundary, /non-diagnostic/);
}

const source = fs.readFileSync(path.join(DEMO, "explorer-saturation-record-v1.js"), "utf8");
for (const marker of [
  "explorerSaturationRecord",
  "dataQuality",
  "safetyReview",
  "professionalRecordBridge",
  "confoundersToReview",
  "supportsToTrial",
  "outputFields",
  "automatedDiagnosis: false",
  "automatedEligibilityDecision: false",
  "protectedInstrumentContent: false",
  "ready_for_human_review",
]) {
  assert.ok(source.includes(marker), `missing professional record marker: ${marker}`);
}
for (const forbidden of [
  "diagnosisScore",
  "diagnosticConclusion",
  "eligibilityDecision: true",
  "protectedInstrumentContent: true",
  "normTable",
  "answerKey",
]) {
  assert.ok(!source.includes(forbidden), `forbidden construct: ${forbidden}`);
}

const institutional = fs.readFileSync(path.join(DEMO, "institutional-live-v2.js"), "utf8");
const contextIndex = institutional.indexOf('"original-tools-session-context-v2.js"');
const progressIndex = institutional.indexOf('"original-tools-progress-v1.js"');
const bridgeIndex = institutional.indexOf('"explorer-saturation-record-v1.js"');
assert.ok(contextIndex >= 0 && progressIndex > contextIndex && bridgeIndex > progressIndex, "context, progress and record bridge must load in order");

console.log(JSON.stringify({
  schema: api.schema,
  toolsWithProfessionalSnapshots: tools.length,
  submitCapture: true,
  guideEnhancement: true,
  recordBridge: true,
  status: "passed",
}, null, 2));
