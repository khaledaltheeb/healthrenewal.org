"use strict";

(() => {
  if (typeof store === "undefined" || !Array.isArray(store?.cases)) return;

  const VERSION = "220.1";
  const canonicalField = "reportIssuedBy";
  const legacyField = "reportIssuer";

  const persist = () => {
    if (typeof set === "function" && typeof storeKey === "function" && identity?.uid) {
      return set(storeKey(identity.uid), store);
    }
    if (typeof save === "function") {
      save();
      return true;
    }
    return false;
  };

  const normalizeRecord = (record, now) => {
    if (!record || typeof record !== "object") return false;
    const legacy = String(record[legacyField] || "").trim();
    const canonical = String(record[canonicalField] || "").trim();
    const structuredPublisher = String(record.professionalMaturity?.instrument?.publisher || "").trim();
    const next = canonical || legacy || structuredPublisher;
    let changed = false;

    if (next && canonical !== next) {
      record[canonicalField] = next;
      changed = true;
    }
    if (Object.prototype.hasOwnProperty.call(record, legacyField)) {
      delete record[legacyField];
      changed = true;
    }
    if (!changed) return false;

    record.metadataAuditTrail ||= [];
    const alreadyLogged = record.metadataAuditTrail.some((entry) =>
      entry?.eventType === "schema_alias_migrated"
      && entry?.fromField === legacyField
      && entry?.toField === canonicalField
    );
    if (!alreadyLogged) {
      record.metadataAuditTrail.push({
        auditId: typeof id === "function" ? id("META") : `META-${Date.now()}`,
        eventType: "schema_alias_migrated",
        changedAt: now,
        changedByUid: identity?.uid || "local-user",
        changedByRole: identity?.role || "local",
        fromField: legacyField,
        toField: canonicalField,
        reason: "توحيد اسم جهة إصدار التقرير مع مخطط سجل التدقيق الأصلي.",
      });
    }
    record.schemaCompatibilityVersion = VERSION;
    return true;
  };

  const normalizeAll = ({ persistChanges = true } = {}) => {
    const now = new Date().toISOString();
    let changed = 0;
    for (const caseRecord of store.cases) {
      let caseChanged = false;
      for (const record of caseRecord.professionalAssessments || []) {
        if (normalizeRecord(record, now)) {
          changed += 1;
          caseChanged = true;
        }
      }
      if (caseChanged) caseRecord.updatedAt = now;
    }
    if (changed && persistChanges) persist();
    return changed;
  };

  const form = document.getElementById("professional-record-form");
  form?.addEventListener("submit", () => {
    queueMicrotask(() => {
      const changed = normalizeAll();
      if (changed && typeof render === "function") render();
    });
  }, true);

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-edit-professional-record]")) return;
    normalizeAll();
  }, true);

  normalizeAll();

  window.PA_PROFESSIONAL_SCHEMA_COMPAT_V220 = Object.freeze({
    version: VERSION,
    canonicalField,
    legacyField,
    normalizeAll,
    migrationAudited: true,
    localOnly: true,
  });
})();
