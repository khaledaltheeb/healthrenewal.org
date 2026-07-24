"use strict";

(() => {
  const PBKDF2_ITERATIONS = 250000;
  const BACKUP_SCHEMA = "pa-demo-uid-backup-v2";
  const ENCRYPTED_SCHEMA = "pa-demo-uid-backup-encrypted-v1";
  const CHUNK_SIZE = 0x8000;

  const isPlainObject = (value) => value && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
  const stableStringify = (value) => {
    if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
    if (isPlainObject(value)) return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    return JSON.stringify(value);
  };
  const bytesToBase64Chunked = (bytes) => {
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += CHUNK_SIZE) {
      binary += String.fromCharCode.apply(null, bytes.subarray(offset, Math.min(offset + CHUNK_SIZE, bytes.length)));
    }
    return btoa(binary);
  };
  const hex = (buffer) => [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  const sha256 = async (value) => hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(stableStringify(value))));
  const countStore = (value) => {
    const cases = Array.isArray(value?.cases) ? value.cases : [];
    return {
      cases: cases.length,
      sessions: cases.reduce((sum, item) => sum + (Array.isArray(item.sessions) ? item.sessions.length : 0), 0),
      professionalRecords: cases.reduce((sum, item) => sum + (Array.isArray(item.professionalAssessments) ? item.professionalAssessments.length : 0), 0),
    };
  };
  const deriveKey = async (passphrase, salt) => {
    const material = await crypto.subtle.importKey("raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey(
      { name: "PBKDF2", salt, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
      material,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt"]
    );
  };

  async function exportEncrypted(form) {
    const passphrase = form.elements.passphrase.value;
    if (passphrase.length < 10) {
      toast("عبارة المرور المشفرة يجب ألا تقل عن 10 رموز.");
      return;
    }
    const exportedAt = new Date().toISOString();
    const data = JSON.parse(JSON.stringify(store));
    const core = {
      schema: BACKUP_SCHEMA,
      backupVersion: 2,
      ownerUid: identity.uid,
      username: identity.username,
      exportedAt,
      manifest: { ...countStore(data), appSchemaVersion: String(data.schemaVersion || "3") },
      data,
    };
    const payload = { ...core, integrity: { algorithm: "SHA-256", digest: await sha256(core) } };
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const key = await deriveKey(passphrase, salt);
    const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(payload))));
    const output = {
      schema: ENCRYPTED_SCHEMA,
      version: 1,
      ownerUid: identity.uid,
      exportedAt,
      kdf: "PBKDF2-SHA-256",
      iterations: PBKDF2_ITERATIONS,
      cipher: "AES-GCM-256",
      salt: bytesToBase64Chunked(salt),
      iv: bytesToBase64Chunked(iv),
      ciphertext: bytesToBase64Chunked(ciphertext),
    };
    const blob = new Blob([JSON.stringify(output, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `provider-assessment-${identity.uid}-encrypted.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
    document.getElementById("backup-export-dialog")?.close();
    form.reset();
    toast("تم تنزيل نسخة مشفرة وموقعة بالبصمة.");
  }

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.id !== "backup-export-form" || !form.elements.encryptBackup?.checked) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!form.reportValidity()) return;
    try {
      await exportEncrypted(form);
    } catch (error) {
      console.error("Encrypted backup export failed", error);
      toast("تعذر إنشاء النسخة الاحتياطية المشفرة.");
    }
  }, true);
})();
