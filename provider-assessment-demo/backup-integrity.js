"use strict";

(() => {
  const BACKUP_SCHEMA = "pa-demo-uid-backup-v2";
  const LEGACY_SCHEMA = "pa-demo-uid-backup-v1";
  const ENCRYPTED_SCHEMA = "pa-demo-uid-backup-encrypted-v1";
  const MAX_FILE_BYTES = 10 * 1024 * 1024;
  const PBKDF2_ITERATIONS = 250000;
  const state = { pending: null, encryptedFile: null };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const isPlainObject = (value) => value && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
  const isDate = (value) => typeof value === "string" && Number.isFinite(Date.parse(value));
  const nowIso = () => new Date().toISOString();
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const bytesToBase64 = (bytes) => btoa(String.fromCharCode(...bytes));
  const base64ToBytes = (value) => Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
  const hex = (buffer) => [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");

  function stableStringify(value) {
    if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
    if (isPlainObject(value)) {
      return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
  }

  async function sha256(value) {
    const data = new TextEncoder().encode(typeof value === "string" ? value : stableStringify(value));
    return hex(await crypto.subtle.digest("SHA-256", data));
  }

  function inspectValue(value, depth = 0, counter = { nodes: 0 }) {
    counter.nodes += 1;
    if (counter.nodes > 120000) throw new Error("too_many_nodes");
    if (depth > 18) throw new Error("too_deep");
    if (value === null || typeof value === "boolean" || typeof value === "number") return value;
    if (typeof value === "string") {
      if (value.length > 20000) throw new Error("string_too_long");
      return value;
    }
    if (Array.isArray(value)) {
      if (value.length > 10000) throw new Error("array_too_large");
      return value.map((item) => inspectValue(item, depth + 1, counter));
    }
    if (!isPlainObject(value)) throw new Error("invalid_object");
    const keys = Object.keys(value);
    if (keys.length > 2000) throw new Error("object_too_large");
    const output = {};
    for (const key of keys) {
      if (["__proto__", "prototype", "constructor"].includes(key)) throw new Error("unsafe_key");
      output[key] = inspectValue(value[key], depth + 1, counter);
    }
    return output;
  }

  const ensureText = (value, fallback = "", max = 1000) => typeof value === "string" ? value.slice(0, max) : fallback;
  const ensureId = (value, prefix) => {
    const clean = ensureText(value, "", 120).trim();
    return clean || (typeof id === "function" ? id(prefix) : `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  };

  function migrateStore(rawStore) {
    const candidate = inspectValue(rawStore);
    if (!isPlainObject(candidate) || !Array.isArray(candidate.cases)) throw new Error("invalid_store");
    if (candidate.cases.length > 500) throw new Error("too_many_cases");

    const migrations = [];
    const warnings = [];
    const caseIds = new Set();
    const sessionIds = new Set();
    const recordIds = new Set();
    let sessionCount = 0;
    let professionalRecordCount = 0;

    const cases = candidate.cases.map((sourceCase, caseIndex) => {
      if (!isPlainObject(sourceCase)) throw new Error("invalid_case");
      const item = clone(sourceCase);
      item.caseId = ensureId(item.caseId, "CASE");
      if (caseIds.has(item.caseId)) {
        const previous = item.caseId;
        item.caseId = ensureId("", "CASE");
        item.importedFromCaseId = previous;
        migrations.push(`تغيير معرف حالة مكرر: ${previous}`);
      }
      caseIds.add(item.caseId);
      item.alias = ensureText(item.alias, `الحالة المستوردة ${caseIndex + 1}`, 120).trim() || `الحالة المستوردة ${caseIndex + 1}`;
      item.question = ensureText(item.question, "سؤال إحالة غير مسجل في النسخة القديمة", 1200);
      item.notes = ensureText(item.notes, "", 5000);
      item.status = ["active", "follow_up", "closed"].includes(item.status) ? item.status : "active";
      item.createdAt = isDate(item.createdAt) ? item.createdAt : nowIso();
      item.updatedAt = isDate(item.updatedAt) ? item.updatedAt : item.createdAt;
      item.sessions = Array.isArray(item.sessions) ? item.sessions : [];
      item.professionalAssessments = Array.isArray(item.professionalAssessments) ? item.professionalAssessments : [];
      if (item.sessions.length > 5000 || item.professionalAssessments.length > 5000) throw new Error("too_many_case_records");

      item.sessions = item.sessions.map((sourceSession) => {
        if (!isPlainObject(sourceSession)) throw new Error("invalid_session");
        const session = clone(sourceSession);
        const original = ensureText(session.sessionId, "", 120);
        session.sessionId = ensureId(session.sessionId, "SES");
        if (sessionIds.has(session.sessionId)) {
          session.importedFromSessionId = original || session.sessionId;
          session.sessionId = ensureId("", "SES");
          migrations.push(`تغيير معرف جلسة مكرر: ${session.importedFromSessionId}`);
        }
        sessionIds.add(session.sessionId);
        session.assessmentId = ensureText(session.assessmentId, "unknown-assessment", 160);
        session.completedAt = isDate(session.completedAt) ? session.completedAt : nowIso();
        session.outcomeLabel = ensureText(session.outcomeLabel, "نتيجة وصفية مستوردة", 300);
        session.summary = ensureText(session.summary, "", 5000);
        session.note = ensureText(session.note, "", 5000);
        sessionCount += 1;
        return session;
      });

      item.professionalAssessments = item.professionalAssessments.map((sourceRecord) => {
        if (!isPlainObject(sourceRecord)) throw new Error("invalid_professional_record");
        const record = clone(sourceRecord);
        const original = ensureText(record.recordId, "", 120);
        record.recordId = ensureId(record.recordId, "PRO");
        if (recordIds.has(record.recordId)) {
          record.importedFromRecordId = original || record.recordId;
          record.recordId = ensureId("", "PRO");
          migrations.push(`تغيير معرف سجل مهني مكرر: ${record.importedFromRecordId}`);
        }
        recordIds.add(record.recordId);
        record.toolId = ensureText(record.toolId, "custom-professional-record", 200);
        record.toolName = ensureText(record.toolName, "خدمة مهنية مستوردة", 300);
        record.category = ensureText(record.category, "مسار مهني", 180);
        record.recordStatus = ["planned", "scheduled", "in_progress", "completed", "result_imported", "incomplete_invalid", "cancelled"].includes(record.recordStatus) ? record.recordStatus : "planned";
        record.auditTrail = Array.isArray(record.auditTrail) ? record.auditTrail : [];
        record.metadataAuditTrail = Array.isArray(record.metadataAuditTrail) ? record.metadataAuditTrail : [];
        record.practitionerQualification = ensureText(record.practitionerQualification, "", 300);
        record.resultSourceType = ensureText(record.resultSourceType, record.administrationMode === "external_import" ? "external_report" : "direct_administration", 120);
        record.reportReference = ensureText(record.reportReference, "", 400);
        record.reportIssuedBy = ensureText(record.reportIssuedBy, "", 300);
        record.recordedAt = isDate(record.recordedAt) ? record.recordedAt : nowIso();
        record.integrityVersion = ensureText(record.integrityVersion, "1.0.0", 40);
        professionalRecordCount += 1;
        return record;
      });
      return item;
    });

    if (sessionCount > 10000) throw new Error("too_many_sessions");
    if (professionalRecordCount > 10000) throw new Error("too_many_professional_records");
    if (String(candidate.schemaVersion || "3") !== "3") warnings.push(`تمت تهيئة مخطط قديم: ${candidate.schemaVersion || "غير مسجل"}`);

    return {
      store: {
        uid: ensureText(candidate.uid, "", 120),
        schemaVersion: "3",
        cases,
        createdAt: isDate(candidate.createdAt) ? candidate.createdAt : nowIso(),
        updatedAt: nowIso(),
        importHistory: Array.isArray(candidate.importHistory) ? candidate.importHistory : [],
      },
      counts: { cases: cases.length, sessions: sessionCount, professionalRecords: professionalRecordCount },
      migrations,
      warnings,
    };
  }

  function countStore(value) {
    const cases = Array.isArray(value?.cases) ? value.cases : [];
    return {
      cases: cases.length,
      sessions: cases.reduce((sum, item) => sum + (Array.isArray(item.sessions) ? item.sessions.length : 0), 0),
      professionalRecords: cases.reduce((sum, item) => sum + (Array.isArray(item.professionalAssessments) ? item.professionalAssessments.length : 0), 0),
    };
  }

  function conflictReport(incoming) {
    const currentCases = new Set(store.cases.map((item) => item.caseId));
    const currentSessions = new Set(store.cases.flatMap((item) => (item.sessions || []).map((entry) => entry.sessionId)));
    const currentRecords = new Set(store.cases.flatMap((item) => (item.professionalAssessments || []).map((entry) => entry.recordId)));
    const incomingCases = incoming.cases.filter((item) => currentCases.has(item.caseId)).length;
    const incomingSessions = incoming.cases.flatMap((item) => item.sessions || []).filter((entry) => currentSessions.has(entry.sessionId)).length;
    const incomingRecords = incoming.cases.flatMap((item) => item.professionalAssessments || []).filter((entry) => currentRecords.has(entry.recordId)).length;
    return { cases: incomingCases, sessions: incomingSessions, professionalRecords: incomingRecords, total: incomingCases + incomingSessions + incomingRecords };
  }

  async function buildBackup() {
    const exportedAt = nowIso();
    const data = clone(store);
    const manifest = { ...countStore(data), appSchemaVersion: String(data.schemaVersion || "3") };
    const core = {
      schema: BACKUP_SCHEMA,
      backupVersion: 2,
      ownerUid: identity.uid,
      username: identity.username,
      exportedAt,
      manifest,
      data,
    };
    return { ...core, integrity: { algorithm: "SHA-256", digest: await sha256(core) } };
  }

  async function deriveKey(passphrase, salt, usage) {
    const material = await crypto.subtle.importKey("raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey(
      { name: "PBKDF2", salt, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
      material,
      { name: "AES-GCM", length: 256 },
      false,
      [usage]
    );
  }

  async function encryptBackup(payload, passphrase) {
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const key = await deriveKey(passphrase, salt, "encrypt");
    const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(payload)));
    return {
      schema: ENCRYPTED_SCHEMA,
      version: 1,
      ownerUid: identity.uid,
      exportedAt: payload.exportedAt,
      kdf: "PBKDF2-SHA-256",
      iterations: PBKDF2_ITERATIONS,
      cipher: "AES-GCM-256",
      salt: bytesToBase64(salt),
      iv: bytesToBase64(iv),
      ciphertext: bytesToBase64(new Uint8Array(ciphertext)),
    };
  }

  async function decryptBackup(payload, passphrase) {
    if (payload.schema !== ENCRYPTED_SCHEMA || payload.iterations !== PBKDF2_ITERATIONS) throw new Error("unsupported_encryption");
    const salt = base64ToBytes(payload.salt);
    const iv = base64ToBytes(payload.iv);
    const ciphertext = base64ToBytes(payload.ciphertext);
    const key = await deriveKey(passphrase, salt, "decrypt");
    const clear = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ciphertext);
    return JSON.parse(new TextDecoder().decode(clear));
  }

  async function validatePayload(payload, fileName) {
    if (!isPlainObject(payload)) throw new Error("invalid_payload");
    let integrityStatus = "legacy";
    let data;
    let sourceUid;
    let exportedAt;
    let schema;

    if (payload.schema === BACKUP_SCHEMA) {
      const core = {
        schema: payload.schema,
        backupVersion: payload.backupVersion,
        ownerUid: payload.ownerUid,
        username: payload.username,
        exportedAt: payload.exportedAt,
        manifest: payload.manifest,
        data: payload.data,
      };
      const expected = ensureText(payload.integrity?.digest, "", 128).toLowerCase();
      const actual = await sha256(core);
      if (!expected || actual !== expected) throw new Error("integrity_mismatch");
      integrityStatus = "verified";
      data = payload.data;
      sourceUid = payload.ownerUid;
      exportedAt = payload.exportedAt;
      schema = BACKUP_SCHEMA;
    } else if (payload.schema === LEGACY_SCHEMA) {
      data = payload.data;
      sourceUid = payload.ownerUid;
      exportedAt = payload.exportedAt;
      schema = LEGACY_SCHEMA;
    } else {
      throw new Error("unsupported_schema");
    }

    if (!sourceUid || typeof sourceUid !== "string") throw new Error("missing_owner_uid");
    const migrated = migrateStore(data);
    const conflicts = conflictReport(migrated.store);
    return {
      fileName,
      schema,
      sourceUid,
      exportedAt: isDate(exportedAt) ? exportedAt : "غير مسجل",
      integrityStatus,
      ...migrated,
      conflicts,
    };
  }

  function remapForMerge(incoming) {
    const result = clone(incoming);
    const caseIds = new Set(store.cases.map((item) => item.caseId));
    const sessionIds = new Set(store.cases.flatMap((item) => item.sessions || []).map((entry) => entry.sessionId));
    const recordIds = new Set(store.cases.flatMap((item) => item.professionalAssessments || []).map((entry) => entry.recordId));
    for (const caseRecord of result.cases) {
      if (caseIds.has(caseRecord.caseId)) {
        caseRecord.importedFromCaseId = caseRecord.caseId;
        caseRecord.caseId = ensureId("", "CASE");
      }
      caseIds.add(caseRecord.caseId);
      for (const session of caseRecord.sessions || []) {
        if (sessionIds.has(session.sessionId)) {
          session.importedFromSessionId = session.sessionId;
          session.sessionId = ensureId("", "SES");
        }
        sessionIds.add(session.sessionId);
      }
      for (const record of caseRecord.professionalAssessments || []) {
        if (recordIds.has(record.recordId)) {
          record.importedFromRecordId = record.recordId;
          record.recordId = ensureId("", "PRO");
        }
        recordIds.add(record.recordId);
      }
    }
    return result;
  }

  function createRollbackSnapshot() {
    const key = `pa-demo-import-rollback-v1:${identity.uid}`;
    const snapshot = { schema: "pa-demo-import-rollback-v1", ownerUid: identity.uid, createdAt: nowIso(), data: clone(store) };
    localStorage.setItem(key, JSON.stringify(snapshot));
    return key;
  }

  function applyImport(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity() || !state.pending) return;
    const sourceMismatch = state.pending.sourceUid !== identity.uid;
    if (sourceMismatch) {
      const allowed = form.elements.allowTransfer.checked;
      const typed = form.elements.transferConfirmation.value.trim();
      if (!allowed || typed !== identity.uid) {
        toast("النقل بين UID يتطلب الموافقة وكتابة UID الحالي كاملًا.");
        return;
      }
    }

    try {
      createRollbackSnapshot();
    } catch (_error) {
      toast("تعذر إنشاء نقطة تراجع محلية؛ أُلغي الاستيراد لحماية البيانات الحالية.");
      return;
    }

    const mode = form.elements.importMode.value;
    const incoming = clone(state.pending.store);
    incoming.uid = identity.uid;
    const importedAt = nowIso();
    const historyEntry = {
      importId: ensureId("", "IMP"),
      importedAt,
      importedByUid: identity.uid,
      sourceUid: state.pending.sourceUid,
      sourceFile: state.pending.fileName,
      sourceSchema: state.pending.schema,
      integrityStatus: state.pending.integrityStatus,
      mode,
      transferredBetweenUids: sourceMismatch,
      migrations: state.pending.migrations.length,
      conflicts: state.pending.conflicts,
    };

    if (sourceMismatch) {
      for (const caseRecord of incoming.cases) {
        caseRecord.transferredFromUid = state.pending.sourceUid;
        caseRecord.transferredAt = importedAt;
      }
    }

    if (mode === "merge") {
      const remapped = remapForMerge(incoming);
      store = {
        ...store,
        cases: [...remapped.cases, ...store.cases],
        importHistory: [...(store.importHistory || []), historyEntry],
        updatedAt: importedAt,
      };
    } else {
      store = {
        ...incoming,
        uid: identity.uid,
        importHistory: [...(incoming.importHistory || []), historyEntry],
        updatedAt: importedAt,
      };
    }

    save();
    render();
    document.getElementById("backup-import-preview-dialog")?.close();
    state.pending = null;
    toast(mode === "merge" ? "تم دمج النسخة بعد التحقق وإنشاء نقطة تراجع." : "تم استبدال المساحة بعد التحقق وإنشاء نقطة تراجع.");
  }

  function restoreRollback() {
    const key = `pa-demo-import-rollback-v1:${identity.uid}`;
    try {
      const snapshot = JSON.parse(localStorage.getItem(key) || "null");
      if (!snapshot || snapshot.ownerUid !== identity.uid || !snapshot.data) throw new Error("missing_snapshot");
      if (!window.confirm(`استعادة حالة المساحة قبل آخر استيراد بتاريخ ${snapshot.createdAt}؟`)) return;
      const migrated = migrateStore(snapshot.data);
      migrated.store.uid = identity.uid;
      store = migrated.store;
      save();
      render();
      localStorage.removeItem(key);
      toast("تم التراجع عن آخر استيراد.");
    } catch (_error) {
      toast("لا توجد نقطة تراجع صالحة لهذا UID.");
    }
  }

  function showPreview(result) {
    state.pending = result;
    const dialog = document.getElementById("backup-import-preview-dialog");
    const form = document.getElementById("backup-import-preview-form");
    const mismatch = result.sourceUid !== identity.uid;
    document.getElementById("backup-import-preview-summary").innerHTML = `
      <div class="stats-grid">
        <article class="stat-card"><span>الحالات</span><strong>${result.counts.cases}</strong></article>
        <article class="stat-card"><span>الجلسات</span><strong>${result.counts.sessions}</strong></article>
        <article class="stat-card"><span>السجلات المهنية</span><strong>${result.counts.professionalRecords}</strong></article>
        <article class="stat-card"><span>التعارضات</span><strong>${result.conflicts.total}</strong></article>
      </div>
      <dl class="summary-grid">
        <div><dt>الملف</dt><dd>${esc(result.fileName)}</dd></div>
        <div><dt>UID المصدر</dt><dd class="code">${esc(result.sourceUid)}</dd></div>
        <div><dt>تاريخ التصدير</dt><dd>${esc(result.exportedAt)}</dd></div>
        <div><dt>سلامة البصمة</dt><dd>${result.integrityStatus === "verified" ? "موثقة SHA-256" : "نسخة قديمة بلا بصمة"}</dd></div>
      </dl>
      ${result.migrations.length ? `<div class="callout info">سيطبق النظام ${result.migrations.length} ترحيلًا أو إصلاح معرف قبل الاستيراد.</div>` : ""}
      ${result.conflicts.total ? `<div class="callout warning">عند الدمج ستُنشأ معرفات جديدة تلقائيًا لـ ${result.conflicts.cases} حالة و${result.conflicts.sessions} جلسة و${result.conflicts.professionalRecords} سجل مهني متعارض.</div>` : ""}
      ${mismatch ? `<div class="callout warning">هذه النسخة تخص UID مختلفًا. لن تُكتب أي بيانات قبل إجراء نقل صريح إلى UID الحالي.</div>` : ""}`;
    form.reset();
    form.elements.importMode.value = store.cases.length ? "merge" : "replace";
    const transfer = document.getElementById("backup-transfer-fields");
    transfer.hidden = !mismatch;
    form.elements.allowTransfer.required = mismatch;
    form.elements.transferConfirmation.required = mismatch;
    document.getElementById("backup-current-uid-confirmation").textContent = identity.uid;
    if (typeof open === "function") open(dialog); else dialog.showModal();
  }

  async function inspectFile(file, passphrase = "") {
    if (!file || file.size <= 0 || file.size > MAX_FILE_BYTES) throw new Error("invalid_file_size");
    let payload = JSON.parse(await file.text());
    if (payload?.schema === ENCRYPTED_SCHEMA) {
      if (!passphrase) {
        state.encryptedFile = file;
        document.getElementById("backup-unlock-form").reset();
        if (typeof open === "function") open(document.getElementById("backup-unlock-dialog")); else document.getElementById("backup-unlock-dialog").showModal();
        return null;
      }
      payload = await decryptBackup(payload, passphrase);
    }
    return validatePayload(payload, file.name);
  }

  async function handleFile(file) {
    try {
      const result = await inspectFile(file);
      if (result) showPreview(result);
    } catch (error) {
      const messages = {
        invalid_file_size: "ملف النسخة فارغ أو يتجاوز 10 ميجابايت.",
        integrity_mismatch: "رُفضت النسخة لأن بصمة SHA-256 لا تطابق محتواها.",
        unsupported_schema: "مخطط النسخة غير مدعوم.",
        unsafe_key: "رُفضت النسخة لاحتوائها على مفاتيح غير آمنة.",
      };
      toast(messages[error.message] || "تعذر فحص النسخة. لم تُكتب أي بيانات.");
    }
  }

  async function submitUnlock(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity() || !state.encryptedFile) return;
    try {
      const result = await inspectFile(state.encryptedFile, form.elements.passphrase.value);
      state.encryptedFile = null;
      document.getElementById("backup-unlock-dialog").close();
      showPreview(result);
    } catch (_error) {
      toast("تعذر فك النسخة. تحقق من عبارة المرور وسلامة الملف.");
    }
  }

  async function submitExport(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    try {
      const payload = await buildBackup();
      const encrypted = form.elements.encryptBackup.checked;
      const passphrase = form.elements.passphrase.value;
      if (encrypted && passphrase.length < 10) {
        toast("عبارة المرور المشفرة يجب ألا تقل عن 10 رموز.");
        return;
      }
      const output = encrypted ? await encryptBackup(payload, passphrase) : payload;
      const blob = new Blob([JSON.stringify(output, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `provider-assessment-${identity.uid}-${encrypted ? "encrypted" : "verified"}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      document.getElementById("backup-export-dialog").close();
      form.reset();
      toast(encrypted ? "تم تنزيل نسخة مشفرة وموقعة بالبصمة." : "تم تنزيل نسخة موثقة ببصمة SHA-256.");
    } catch (_error) {
      toast("تعذر إنشاء النسخة الاحتياطية.");
    }
  }

  function installUi() {
    if (document.getElementById("backup-export-dialog")) return;
    const style = document.createElement("style");
    style.textContent = `.backup-integrity-note{margin-top:10px;font-size:.9rem;color:var(--muted)}.backup-security-grid{display:grid;gap:10px}.backup-transfer-box{border:1px solid #d4b65d;background:#fff9e8;border-radius:14px;padding:14px}.backup-transfer-box[hidden]{display:none}.backup-preview-scroll{max-height:60vh;overflow:auto;padding-inline-end:4px}`;
    document.head.appendChild(style);

    const exportDialog = document.createElement("dialog");
    exportDialog.id = "backup-export-dialog";
    exportDialog.className = "dialog large";
    exportDialog.innerHTML = `<form method="dialog" id="backup-export-form"><div class="dialog-heading"><div><p class="eyebrow">نسخة موثقة قابلة للتحقق</p><h2>تصدير مساحة UID</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div><div class="callout info">تتضمن النسخة مخططًا واضحًا، أعداد السجلات، وبصمة SHA-256 لاكتشاف أي تعديل بعد التنزيل.</div><div class="backup-security-grid"><label class="rights-confirmation"><input name="encryptBackup" type="checkbox"><span>تشفير النسخة بعبارة مرور باستخدام AES-GCM وPBKDF2.</span></label><label class="field"><span>عبارة المرور عند التشفير</span><input name="passphrase" type="password" minlength="10" maxlength="200" autocomplete="new-password" placeholder="10 رموز على الأقل"></label></div><p class="backup-integrity-note">لا يمكن استعادة العبارة المنسية، ولا تُرسل العبارة أو البيانات إلى أي خادم.</p><div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">تنزيل النسخة</button></div></form>`;

    const previewDialog = document.createElement("dialog");
    previewDialog.id = "backup-import-preview-dialog";
    previewDialog.className = "dialog xlarge";
    previewDialog.innerHTML = `<form method="dialog" id="backup-import-preview-form"><div class="dialog-heading"><div><p class="eyebrow">لا كتابة قبل المعاينة</p><h2>مراجعة النسخة قبل الاستيراد</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div><div id="backup-import-preview-summary" class="backup-preview-scroll"></div><label class="field"><span>طريقة الاستيراد</span><select name="importMode" required><option value="merge">دمج مع البيانات الحالية ومعالجة التعارضات</option><option value="replace">استبدال المساحة الحالية بالكامل</option></select></label><div id="backup-transfer-fields" class="backup-transfer-box" hidden><p><strong>نقل صريح بين UID</strong></p><label class="rights-confirmation"><input name="allowTransfer" type="checkbox"><span>أوافق على نقل هذه النسخة إلى UID الحالي مع توثيق UID المصدر.</span></label><label class="field"><span>اكتب UID الحالي للتأكيد</span><input name="transferConfirmation" autocomplete="off"><small id="backup-current-uid-confirmation" class="code"></small></label></div><div class="callout info">سينشئ النظام نقطة تراجع محلية قبل أي كتابة. لا تُستورد ملفات أو بنود مقاييس؛ الاستيراد يخص السجلات الوصفية فقط.</div><div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">تنفيذ الاستيراد</button></div></form>`;

    const unlockDialog = document.createElement("dialog");
    unlockDialog.id = "backup-unlock-dialog";
    unlockDialog.className = "dialog";
    unlockDialog.innerHTML = `<form method="dialog" id="backup-unlock-form"><div class="dialog-heading"><div><p class="eyebrow">AES-GCM</p><h2>فك النسخة المشفرة</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div><label class="field"><span>عبارة المرور</span><input name="passphrase" type="password" minlength="10" maxlength="200" required autocomplete="current-password"></label><div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">فك وفحص النسخة</button></div></form>`;
    document.body.append(exportDialog, previewDialog, unlockDialog);

    const addRollbackButton = () => {
      const actions = document.querySelector(".backup-actions");
      if (!actions || document.getElementById("rollback-space-import")) return;
      const button = document.createElement("button");
      button.id = "rollback-space-import";
      button.className = "button ghost";
      button.type = "button";
      button.textContent = "التراجع عن آخر استيراد";
      actions.appendChild(button);
      const note = document.createElement("p");
      note.className = "backup-integrity-note";
      note.textContent = "النسخ الجديدة تدعم البصمة، التشفير الاختياري، المعاينة، الدمج، ونقطة التراجع.";
      actions.closest(".backup-panel")?.appendChild(note);
    };
    addRollbackButton();
    new MutationObserver(addRollbackButton).observe(document.body, { childList: true, subtree: true });
  }

  installUi();
  document.getElementById("backup-export-form")?.addEventListener("submit", submitExport);
  document.getElementById("backup-import-preview-form")?.addEventListener("submit", applyImport);
  document.getElementById("backup-unlock-form")?.addEventListener("submit", submitUnlock);

  document.addEventListener("click", (event) => {
    const target = event.target.closest("button");
    if (!target) return;
    if (target.id === "export-space") {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (typeof open === "function") open(document.getElementById("backup-export-dialog")); else document.getElementById("backup-export-dialog").showModal();
    }
    if (target.id === "import-space") {
      event.preventDefault();
      event.stopImmediatePropagation();
      document.getElementById("import-space-file")?.click();
    }
    if (target.id === "rollback-space-import") {
      event.preventDefault();
      event.stopImmediatePropagation();
      restoreRollback();
    }
  }, true);

  document.addEventListener("change", (event) => {
    if (event.target.id !== "import-space-file") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const file = event.target.files?.[0];
    event.target.value = "";
    handleFile(file);
  }, true);
})();
