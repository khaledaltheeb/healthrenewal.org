"use strict";

(() => {
  const BACKUP_SCHEMA = "pa-demo-uid-backup-v2";
  const LEGACY_SCHEMA = "pa-demo-uid-backup-v1";
  const ENCRYPTED_SCHEMA = "pa-demo-uid-backup-encrypted-v1";
  const PBKDF2_ITERATIONS = 250000;
  const MAX_FILE_BYTES = 10 * 1024 * 1024;
  const state = { pending: null, encryptedFile: null };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const nowIso = () => new Date().toISOString();
  const isDate = (value) => typeof value === "string" && Number.isFinite(Date.parse(value));
  const isPlainObject = (value) => value && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
  const text = (value, fallback = "", max = 2000) => typeof value === "string" ? value.slice(0, max) : fallback;
  const newId = (prefix) => typeof id === "function" ? id(prefix) : `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  const ensureId = (value, prefix) => text(value, "", 120).trim() || newId(prefix);
  const toHex = (buffer) => [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");

  function bytesToBase64(bytes) {
    let binary = "";
    const chunkSize = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(offset, Math.min(offset + chunkSize, bytes.length)));
    }
    return btoa(binary);
  }

  function base64ToBytes(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  }

  function stableStringify(value) {
    if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
    if (isPlainObject(value)) {
      return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
  }

  async function sha256(value) {
    const bytes = new TextEncoder().encode(typeof value === "string" ? value : stableStringify(value));
    return toHex(await crypto.subtle.digest("SHA-256", bytes));
  }

  function inspectJson(value, depth = 0, counter = { nodes: 0 }) {
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
      return value.map((item) => inspectJson(item, depth + 1, counter));
    }
    if (!isPlainObject(value)) throw new Error("invalid_object");
    const keys = Object.keys(value);
    if (keys.length > 2000) throw new Error("object_too_large");
    const output = {};
    for (const key of keys) {
      if (["__proto__", "prototype", "constructor"].includes(key)) throw new Error("unsafe_key");
      output[key] = inspectJson(value[key], depth + 1, counter);
    }
    return output;
  }

  function countStore(candidate) {
    const cases = Array.isArray(candidate?.cases) ? candidate.cases : [];
    return {
      cases: cases.length,
      sessions: cases.reduce((sum, item) => sum + (Array.isArray(item.sessions) ? item.sessions.length : 0), 0),
      professionalRecords: cases.reduce((sum, item) => sum + (Array.isArray(item.professionalAssessments) ? item.professionalAssessments.length : 0), 0),
    };
  }

  function migrateStore(rawStore) {
    const candidate = inspectJson(rawStore);
    if (!isPlainObject(candidate) || !Array.isArray(candidate.cases)) throw new Error("invalid_store");
    if (candidate.cases.length > 500) throw new Error("too_many_cases");

    const migrations = [];
    const warnings = [];
    const caseIds = new Set();
    const sessionIds = new Set();
    const recordIds = new Set();

    const cases = candidate.cases.map((sourceCase, caseIndex) => {
      if (!isPlainObject(sourceCase)) throw new Error("invalid_case");
      const item = clone(sourceCase);
      item.caseId = ensureId(item.caseId, "CASE");
      if (caseIds.has(item.caseId)) {
        item.importedFromCaseId = item.caseId;
        item.caseId = newId("CASE");
        migrations.push(`إعادة ترقيم حالة مكررة: ${item.importedFromCaseId}`);
      }
      caseIds.add(item.caseId);
      item.alias = text(item.alias, `الحالة المستوردة ${caseIndex + 1}`, 120).trim() || `الحالة المستوردة ${caseIndex + 1}`;
      item.question = text(item.question, "سؤال إحالة غير مسجل في النسخة القديمة", 1200);
      item.notes = text(item.notes, "", 5000);
      item.status = ["active", "follow_up", "closed"].includes(item.status) ? item.status : "active";
      item.createdAt = isDate(item.createdAt) ? item.createdAt : nowIso();
      item.updatedAt = isDate(item.updatedAt) ? item.updatedAt : item.createdAt;
      item.sessions = Array.isArray(item.sessions) ? item.sessions : [];
      item.professionalAssessments = Array.isArray(item.professionalAssessments) ? item.professionalAssessments : [];
      if (item.sessions.length > 5000 || item.professionalAssessments.length > 5000) throw new Error("too_many_case_records");

      item.sessions = item.sessions.map((sourceSession) => {
        if (!isPlainObject(sourceSession)) throw new Error("invalid_session");
        const session = clone(sourceSession);
        session.sessionId = ensureId(session.sessionId, "SES");
        if (sessionIds.has(session.sessionId)) {
          session.importedFromSessionId = session.sessionId;
          session.sessionId = newId("SES");
          migrations.push(`إعادة ترقيم جلسة مكررة: ${session.importedFromSessionId}`);
        }
        sessionIds.add(session.sessionId);
        session.assessmentId = text(session.assessmentId, "unknown-assessment", 160);
        session.completedAt = isDate(session.completedAt) ? session.completedAt : nowIso();
        session.outcomeLabel = text(session.outcomeLabel, "نتيجة وصفية مستوردة", 300);
        session.summary = text(session.summary, "", 5000);
        session.note = text(session.note, "", 5000);
        return session;
      });

      item.professionalAssessments = item.professionalAssessments.map((sourceRecord) => {
        if (!isPlainObject(sourceRecord)) throw new Error("invalid_professional_record");
        const record = clone(sourceRecord);
        record.recordId = ensureId(record.recordId, "PRO");
        if (recordIds.has(record.recordId)) {
          record.importedFromRecordId = record.recordId;
          record.recordId = newId("PRO");
          migrations.push(`إعادة ترقيم سجل مهني مكرر: ${record.importedFromRecordId}`);
        }
        recordIds.add(record.recordId);
        record.toolId = text(record.toolId, "custom-professional-record", 200);
        record.toolName = text(record.toolName, "خدمة مهنية مستوردة", 300);
        record.category = text(record.category, "مسار مهني", 180);
        record.recordStatus = ["planned", "scheduled", "in_progress", "completed", "result_imported", "incomplete_invalid", "cancelled"].includes(record.recordStatus) ? record.recordStatus : "planned";
        record.auditTrail = Array.isArray(record.auditTrail) ? record.auditTrail : [];
        record.metadataAuditTrail = Array.isArray(record.metadataAuditTrail) ? record.metadataAuditTrail : [];
        record.practitionerQualification = text(record.practitionerQualification, "", 300);
        record.resultSourceType = text(record.resultSourceType, record.administrationMode === "external_import" ? "external_report" : "direct_administration", 120);
        record.reportReference = text(record.reportReference, "", 400);
        record.reportIssuedBy = text(record.reportIssuedBy, "", 300);
        record.recordedAt = isDate(record.recordedAt) ? record.recordedAt : nowIso();
        record.integrityVersion = text(record.integrityVersion, "1.0.0", 40);
        return record;
      });
      return item;
    });

    const output = {
      uid: text(candidate.uid, "", 120),
      schemaVersion: "3",
      cases,
      createdAt: isDate(candidate.createdAt) ? candidate.createdAt : nowIso(),
      updatedAt: nowIso(),
      importHistory: Array.isArray(candidate.importHistory) ? candidate.importHistory : [],
    };
    const counts = countStore(output);
    if (counts.sessions > 10000) throw new Error("too_many_sessions");
    if (counts.professionalRecords > 10000) throw new Error("too_many_professional_records");
    if (String(candidate.schemaVersion || "3") !== "3") warnings.push(`تهيئة مخطط قديم: ${candidate.schemaVersion || "غير مسجل"}`);
    return { store: output, counts, migrations, warnings };
  }

  function conflictReport(incoming) {
    const existingCases = new Set(store.cases.map((item) => item.caseId));
    const existingSessions = new Set(store.cases.flatMap((item) => item.sessions || []).map((item) => item.sessionId));
    const existingRecords = new Set(store.cases.flatMap((item) => item.professionalAssessments || []).map((item) => item.recordId));
    const cases = incoming.cases.filter((item) => existingCases.has(item.caseId)).length;
    const sessions = incoming.cases.flatMap((item) => item.sessions || []).filter((item) => existingSessions.has(item.sessionId)).length;
    const professionalRecords = incoming.cases.flatMap((item) => item.professionalAssessments || []).filter((item) => existingRecords.has(item.recordId)).length;
    return { cases, sessions, professionalRecords, total: cases + sessions + professionalRecords };
  }

  async function buildBackup() {
    const data = clone(store);
    const manifest = { ...countStore(data), appSchemaVersion: String(data.schemaVersion || "3") };
    const core = {
      schema: BACKUP_SCHEMA,
      backupVersion: 2,
      ownerUid: identity.uid,
      username: identity.username,
      exportedAt: nowIso(),
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
    let data;
    let sourceUid;
    let exportedAt;
    let schema;
    let integrityStatus = "legacy";
    let manifest = null;

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
      const expected = text(payload.integrity?.digest, "", 128).toLowerCase();
      const actual = await sha256(core);
      if (!expected || actual !== expected) throw new Error("integrity_mismatch");
      data = payload.data;
      sourceUid = payload.ownerUid;
      exportedAt = payload.exportedAt;
      schema = BACKUP_SCHEMA;
      manifest = payload.manifest;
      integrityStatus = "verified";
    } else if (payload.schema === LEGACY_SCHEMA) {
      data = payload.data;
      sourceUid = payload.ownerUid;
      exportedAt = payload.exportedAt;
      schema = LEGACY_SCHEMA;
    } else {
      throw new Error("unsupported_schema");
    }

    if (typeof sourceUid !== "string" || !sourceUid.trim()) throw new Error("missing_owner_uid");
    const migrated = migrateStore(data);
    if (migrated.store.uid && migrated.store.uid !== sourceUid) throw new Error("owner_store_mismatch");
    if (manifest) {
      const declared = [manifest.cases, manifest.sessions, manifest.professionalRecords].map(Number);
      const actual = [migrated.counts.cases, migrated.counts.sessions, migrated.counts.professionalRecords];
      if (declared.some((value, index) => !Number.isFinite(value) || value !== actual[index])) throw new Error("manifest_mismatch");
    }
    return {
      fileName,
      schema,
      sourceUid,
      exportedAt: isDate(exportedAt) ? exportedAt : "غير مسجل",
      integrityStatus,
      conflicts: conflictReport(migrated.store),
      ...migrated,
    };
  }

  function remapForMerge(incoming) {
    const output = clone(incoming);
    const caseIds = new Set(store.cases.map((item) => item.caseId));
    const sessionIds = new Set(store.cases.flatMap((item) => item.sessions || []).map((item) => item.sessionId));
    const recordIds = new Set(store.cases.flatMap((item) => item.professionalAssessments || []).map((item) => item.recordId));
    for (const caseRecord of output.cases) {
      if (caseIds.has(caseRecord.caseId)) {
        caseRecord.importedFromCaseId = caseRecord.caseId;
        caseRecord.caseId = newId("CASE");
      }
      caseIds.add(caseRecord.caseId);
      for (const session of caseRecord.sessions || []) {
        if (sessionIds.has(session.sessionId)) {
          session.importedFromSessionId = session.sessionId;
          session.sessionId = newId("SES");
        }
        sessionIds.add(session.sessionId);
      }
      for (const record of caseRecord.professionalAssessments || []) {
        if (recordIds.has(record.recordId)) {
          record.importedFromRecordId = record.recordId;
          record.recordId = newId("PRO");
        }
        recordIds.add(record.recordId);
      }
    }
    return output;
  }

  function createRollbackSnapshot() {
    const key = `pa-demo-import-rollback-v1:${identity.uid}`;
    localStorage.setItem(key, JSON.stringify({
      schema: "pa-demo-import-rollback-v1",
      ownerUid: identity.uid,
      createdAt: nowIso(),
      data: clone(store),
    }));
  }

  function applyImport(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity() || !state.pending) return;
    const sourceUid = state.pending.sourceUid;
    const sourceMismatch = sourceUid !== identity.uid;
    if (sourceMismatch) {
      const typed = form.elements.transferConfirmation.value.trim();
      if (!form.elements.allowTransfer.checked || typed !== identity.uid) {
        toast("النقل بين UID يتطلب الموافقة وكتابة UID الحالي كاملًا.");
        return;
      }
    }

    try {
      createRollbackSnapshot();
    } catch (_error) {
      toast("تعذر إنشاء نقطة تراجع؛ أُلغي الاستيراد لحماية البيانات الحالية.");
      return;
    }

    const mode = form.elements.importMode.value;
    const incoming = clone(state.pending.store);
    incoming.uid = identity.uid;
    const importedAt = nowIso();
    const history = {
      importId: newId("IMP"),
      importedAt,
      importedByUid: identity.uid,
      sourceUid,
      sourceFile: state.pending.fileName,
      sourceSchema: state.pending.schema,
      integrityStatus: state.pending.integrityStatus,
      mode,
      transferredBetweenUids: sourceMismatch,
      migrations: state.pending.migrations.length,
      conflicts: state.pending.conflicts,
    };

    if (sourceMismatch) {
      incoming.cases.forEach((item) => {
        item.transferredFromUid = sourceUid;
        item.transferredAt = importedAt;
      });
    }

    if (mode === "merge") {
      const remapped = remapForMerge(incoming);
      store = {
        ...store,
        cases: [...remapped.cases, ...store.cases],
        importHistory: [...(store.importHistory || []), history],
        updatedAt: importedAt,
      };
    } else {
      store = {
        ...incoming,
        uid: identity.uid,
        importHistory: [...(incoming.importHistory || []), history],
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
    try {
      const key = `pa-demo-import-rollback-v1:${identity.uid}`;
      const snapshot = JSON.parse(localStorage.getItem(key) || "null");
      if (!snapshot || snapshot.ownerUid !== identity.uid || !snapshot.data) throw new Error("missing_snapshot");
      if (!window.confirm(`استعادة المساحة قبل آخر استيراد بتاريخ ${snapshot.createdAt}؟`)) return;
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
        <div><dt>سلامة النسخة</dt><dd>${result.integrityStatus === "verified" ? "بصمة SHA-256 مطابقة" : "نسخة قديمة بلا بصمة"}</dd></div>
      </dl>
      ${result.migrations.length ? `<div class="callout info">سيطبق النظام ${result.migrations.length} ترحيلًا أو إصلاح معرف.</div>` : ""}
      ${result.conflicts.total ? `<div class="callout warning">عند الدمج ستنشأ معرفات جديدة تلقائيًا للتعارضات: ${result.conflicts.cases} حالة، ${result.conflicts.sessions} جلسة، ${result.conflicts.professionalRecords} سجل مهني.</div>` : ""}
      ${mismatch ? `<div class="callout warning">النسخة تخص UID مختلفًا؛ النقل الصريح إلزامي.</div>` : ""}`;
    form.reset();
    form.elements.importMode.value = store.cases.length ? "merge" : "replace";
    const transfer = document.getElementById("backup-transfer-fields");
    transfer.hidden = !mismatch;
    form.elements.allowTransfer.required = mismatch;
    form.elements.transferConfirmation.required = mismatch;
    document.getElementById("backup-current-uid-confirmation").textContent = identity.uid;
    if (typeof open === "function") open(document.getElementById("backup-import-preview-dialog"));
    else document.getElementById("backup-import-preview-dialog").showModal();
  }

  async function inspectFile(file, passphrase = "") {
    if (!file || file.size <= 0 || file.size > MAX_FILE_BYTES) throw new Error("invalid_file_size");
    let payload = JSON.parse(await file.text());
    if (payload?.schema === ENCRYPTED_SCHEMA) {
      if (!passphrase) {
        state.encryptedFile = file;
        document.getElementById("backup-unlock-form").reset();
        if (typeof open === "function") open(document.getElementById("backup-unlock-dialog"));
        else document.getElementById("backup-unlock-dialog").showModal();
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
        invalid_file_size: "الملف فارغ أو يتجاوز 10 ميجابايت.",
        integrity_mismatch: "رُفضت النسخة لأن بصمة SHA-256 لا تطابق المحتوى.",
        manifest_mismatch: "رُفضت النسخة لأن أعداد manifest لا تطابق السجلات الفعلية.",
        owner_store_mismatch: "رُفضت النسخة بسبب تعارض UID المالك مع مخزن البيانات.",
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
      const backup = await buildBackup();
      const encrypted = form.elements.encryptBackup.checked;
      const passphrase = form.elements.passphrase.value;
      if (encrypted && passphrase.length < 10) {
        toast("عبارة المرور يجب ألا تقل عن 10 رموز.");
        return;
      }
      const output = encrypted ? await encryptBackup(backup, passphrase) : backup;
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
      toast(encrypted ? "تم تنزيل نسخة مشفرة وموثقة بالبصمة." : "تم تنزيل نسخة موثقة ببصمة SHA-256.");
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
    exportDialog.innerHTML = `<form method="dialog" id="backup-export-form"><div class="dialog-heading"><div><p class="eyebrow">نسخة قابلة للتحقق</p><h2>تصدير مساحة UID</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div><div class="callout info">تتضمن النسخة manifest وبصمة SHA-256. يمكن إضافة تشفير AES-GCM محلي.</div><div class="backup-security-grid"><label class="rights-confirmation"><input name="encryptBackup" type="checkbox"><span>تشفير النسخة بعبارة مرور.</span></label><label class="field"><span>عبارة المرور</span><input name="passphrase" type="password" minlength="10" maxlength="200" autocomplete="new-password" placeholder="10 رموز على الأقل"></label></div><p class="backup-integrity-note">لا تحفظ عبارة المرور ولا ترسل البيانات إلى خادم.</p><div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">تنزيل النسخة</button></div></form>`;

    const previewDialog = document.createElement("dialog");
    previewDialog.id = "backup-import-preview-dialog";
    previewDialog.className = "dialog xlarge";
    previewDialog.innerHTML = `<form method="dialog" id="backup-import-preview-form"><div class="dialog-heading"><div><p class="eyebrow">لا كتابة قبل المعاينة</p><h2>مراجعة النسخة قبل الاستيراد</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div><div id="backup-import-preview-summary" class="backup-preview-scroll"></div><label class="field"><span>طريقة الاستيراد</span><select name="importMode" required><option value="merge">دمج ومعالجة التعارضات</option><option value="replace">استبدال المساحة الحالية</option></select></label><div id="backup-transfer-fields" class="backup-transfer-box" hidden><p><strong>نقل صريح بين UID</strong></p><label class="rights-confirmation"><input name="allowTransfer" type="checkbox"><span>أوافق على النقل مع توثيق UID المصدر.</span></label><label class="field"><span>اكتب UID الحالي للتأكيد</span><input name="transferConfirmation" autocomplete="off"><small id="backup-current-uid-confirmation" class="code"></small></label></div><div class="callout info">سينشئ النظام نقطة تراجع قبل الكتابة. الاستيراد يخص السجلات الوصفية ولا يضيف مواد مقاييس محمية.</div><div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">تنفيذ الاستيراد</button></div></form>`;

    const unlockDialog = document.createElement("dialog");
    unlockDialog.id = "backup-unlock-dialog";
    unlockDialog.className = "dialog";
    unlockDialog.innerHTML = `<form method="dialog" id="backup-unlock-form"><div class="dialog-heading"><div><p class="eyebrow">AES-GCM</p><h2>فك النسخة المشفرة</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div><label class="field"><span>عبارة المرور</span><input name="passphrase" type="password" minlength="10" maxlength="200" required autocomplete="current-password"></label><div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">فك وفحص النسخة</button></div></form>`;
    document.body.append(exportDialog, previewDialog, unlockDialog);

    const addRollback = () => {
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
      note.textContent = "النسخ الجديدة تدعم البصمة، التشفير، المعاينة، الدمج، ونقطة التراجع.";
      actions.closest(".backup-panel")?.appendChild(note);
    };
    addRollback();
    new MutationObserver(addRollback).observe(document.body, { childList: true, subtree: true });
  }

  installUi();
  document.getElementById("backup-export-form")?.addEventListener("submit", submitExport);
  document.getElementById("backup-import-preview-form")?.addEventListener("submit", applyImport);
  document.getElementById("backup-unlock-form")?.addEventListener("submit", submitUnlock);

  document.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.id === "export-space") {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (typeof open === "function") open(document.getElementById("backup-export-dialog"));
      else document.getElementById("backup-export-dialog").showModal();
    }
    if (button.id === "import-space") {
      event.preventDefault();
      event.stopImmediatePropagation();
      document.getElementById("import-space-file")?.click();
    }
    if (button.id === "rollback-space-import") {
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
