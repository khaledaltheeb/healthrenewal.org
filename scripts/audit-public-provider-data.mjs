#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import process from 'node:process';

const PROVIDERS_PATH = 'specialists-partners/data/providers.json';
const LEDGER_PATH = 'specialists-partners/data/verification-ledger.json';

const forbiddenKeyPatterns = [
  /(^|_)(private|secret|password|passphrase|token|session|cookie|csrf|turnstile)(_|$)/i,
  /(^|_)(email|phone|mobile|whatsapp|address|national_?id|passport|identity)(_|$)/i,
  /(^|_)(document|certificate|license_?image|signature|client|child|case)(_|$)/i,
];

const forbiddenValuePatterns = [
  { label: 'private key', pattern: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i },
  { label: 'credential-like token', pattern: /(?:session|access|refresh|csrf|turnstile)[-_ ]?token\s*[:=]/i },
  { label: 'executable URI scheme', pattern: /(?:^|[\s"'=(])(?:javascript|vbscript|file|blob):/i },
  { label: 'embedded data URI', pattern: /(?:^|[\s"'=(])data:/i },
  { label: 'email address', pattern: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b/i },
  { label: 'telephone URI', pattern: /\btel:\s*\+?[0-9][0-9().\s-]{5,}/i },
  { label: 'raw international phone number', pattern: /(?:^|[^\p{L}\p{N}])\+[0-9](?:[0-9().\s-]*[0-9]){7,14}(?=$|[^\p{L}\p{N}])/u },
  { label: 'WhatsApp contact URL', pattern: /https?:\/\/(?:wa\.me|api\.whatsapp\.com)\//i },
];

const allowedPublicStatuses = new Set(['published']);
const allowedVerificationStatuses = new Set(['approved']);

function fail(message) {
  console.error(`::error::${message}`);
  process.exitCode = 1;
}

function normalizeKey(key) {
  return String(key)
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .toLowerCase();
}

function isForbiddenKey(key) {
  const normalized = normalizeKey(key);
  return forbiddenKeyPatterns.some(pattern => pattern.test(normalized));
}

function safeDecodeURIComponent(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function uriScanVariants(value) {
  const variants = new Set([value, safeDecodeURIComponent(value)]);
  for (const candidate of [...variants]) {
    const normalized = candidate
      .normalize('NFKC')
      .replace(/[\u0000-\u001F\u007F-\u009F\u00AD\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]/gu, '');
    variants.add(normalized);
  }
  return [...variants];
}

function findForbiddenValue(value) {
  if (typeof value !== 'string') return null;
  for (const forbidden of forbiddenValuePatterns) {
    const variants = forbidden.label === 'executable URI scheme' || forbidden.label === 'embedded data URI'
      ? uriScanVariants(value)
      : [value];
    if (variants.some(candidate => forbidden.pattern.test(candidate))) return forbidden;
  }
  return null;
}

function runSelfTests() {
  const blockedKeys = ['email','emailAddress','private_email','nationalId','national-id','licenseImage','csrfToken','turnstile_response','childCase'];
  const allowedKeys = ['displayName','specialty','region','publicationStatus','verificationDecisionId','reviewedAt'];
  const blockedValues = [
    ['generic contact field with email', 'reviewer@example.org'],
    ['generic contact field with telephone URI', 'tel:+962 7 9000 0000'],
    ['generic contact field with raw international number', 'للتواصل +962 79 000 0000'],
    ['generic contact field with compact international number', '+962790000000'],
    ['generic contact field with WhatsApp URL', 'https://wa.me/962790000000'],
    ['generic link field with JavaScript URI', 'javascript:alert(document.domain)'],
    ['generic link field with mixed-case JavaScript URI', 'JaVaScRiPt:alert(1)'],
    ['generic link field with control-obfuscated JavaScript URI', 'java\u0000script:alert(1)'],
    ['generic link field with newline-obfuscated JavaScript URI', 'java\nscript:alert(1)'],
    ['generic link field with fullwidth JavaScript URI', 'ｊａｖａｓｃｒｉｐｔ:alert(1)'],
    ['generic link field with percent-encoded JavaScript separator', 'javascript%3Aalert(1)'],
    ['generic link field with VBScript URI', 'vbscript:msgbox(1)'],
    ['generic link field with file URI', 'file:///etc/passwd'],
    ['generic link field with blob URI', 'blob:https://example.org/identifier'],
    ['generic field with HTML data URI', 'data:text/html,<script>alert(1)</script>'],
    ['generic field with obfuscated HTML data URI', 'da\u200Bta:text/html,<script>alert(1)</script>'],
    ['generic field with embedded document', 'data:application/pdf;base64,JVBERi0xLjQ='],
    ['generic field with credential marker', 'access_token=not-a-real-token'],
  ];
  const allowedValues = [
    'عمّان',
    'اختصاصي نطق ولغة',
    'https://example.org/public-profile',
    'https://example.org/data:overview',
    'https://example.org/javascript:overview',
    'قرار مراجعة عام غير كاشف',
    'إصدار السياسة 2026-07-29',
    'معرّف القرار 962790000000',
  ];

  for (const key of blockedKeys) if (!isForbiddenKey(key)) fail(`self-test: expected forbidden key to be blocked: ${key}`);
  for (const key of allowedKeys) if (isForbiddenKey(key)) fail(`self-test: expected public key to remain allowed: ${key}`);
  for (const [description, value] of blockedValues) if (!findForbiddenValue(value)) fail(`self-test: expected forbidden value to be blocked: ${description}`);
  for (const value of allowedValues) if (findForbiddenValue(value)) fail(`self-test: expected public value to remain allowed: ${value}`);

  if (!process.exitCode) console.log('Public provider data privacy self-test passed.');
}

async function loadJson(path) {
  try {
    return JSON.parse(await readFile(path, 'utf8'));
  } catch (error) {
    fail(`${path}: invalid JSON (${error.message})`);
    return null;
  }
}

function walk(value, path, visitor) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => walk(item, `${path}[${index}]`, visitor));
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, item] of Object.entries(value)) {
    const next = `${path}.${key}`;
    visitor(key, item, next);
    walk(item, next, visitor);
  }
}

function auditForbiddenData(root, rootName) {
  walk(root, rootName, (key, value, path) => {
    if (isForbiddenKey(key)) fail(`${path}: forbidden private or credential-like field in a public file`);
    const forbiddenValue = findForbiddenValue(value);
    if (forbiddenValue) fail(`${path}: forbidden ${forbiddenValue.label} in a public file`);
  });
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

if (process.argv.includes('--self-test')) {
  runSelfTests();
  process.exit(process.exitCode || 0);
}

const providersDoc = await loadJson(PROVIDERS_PATH);
const ledgerDoc = await loadJson(LEDGER_PATH);
if (!providersDoc || !ledgerDoc) process.exit(process.exitCode || 1);

auditForbiddenData(providersDoc, 'providers');
auditForbiddenData(ledgerDoc, 'ledger');

if (!Array.isArray(providersDoc.providers)) fail(`${PROVIDERS_PATH}: providers must be an array`);
if (!Array.isArray(ledgerDoc.records)) fail(`${LEDGER_PATH}: records must be an array`);

const recordsByProvider = new Map();
for (const [index, record] of (ledgerDoc.records || []).entries()) {
  const path = `ledger.records[${index}]`;
  if (!nonEmptyString(record.providerId)) {
    fail(`${path}.providerId: required`);
    continue;
  }
  if (recordsByProvider.has(record.providerId)) fail(`${path}.providerId: duplicate ledger record`);
  recordsByProvider.set(record.providerId, record);
  if (!allowedVerificationStatuses.has(record.status)) fail(`${path}.status: public verification ledger records must be approved only`);
  if (!nonEmptyString(record.decisionId)) fail(`${path}.decisionId: required non-sensitive audit reference`);
  if (!nonEmptyString(record.reviewedAt) || Number.isNaN(Date.parse(record.reviewedAt))) fail(`${path}.reviewedAt: required valid timestamp`);
}

const providerIds = new Set();
for (const [index, provider] of (providersDoc.providers || []).entries()) {
  const path = `providers.providers[${index}]`;
  if (!nonEmptyString(provider.id)) {
    fail(`${path}.id: required`);
    continue;
  }
  if (providerIds.has(provider.id)) fail(`${path}.id: duplicate provider id`);
  providerIds.add(provider.id);
  if (!allowedPublicStatuses.has(provider.publicationStatus)) fail(`${path}.publicationStatus: public directory entries must be published only`);
  const record = recordsByProvider.get(provider.id);
  if (!record) {
    fail(`${path}: published provider has no approved verification-ledger record`);
    continue;
  }
  if (provider.verificationDecisionId !== record.decisionId) fail(`${path}.verificationDecisionId: must match the ledger decisionId`);
  if (!nonEmptyString(provider.displayName)) fail(`${path}.displayName: required`);
}

for (const providerId of recordsByProvider.keys()) {
  if (!providerIds.has(providerId)) fail(`ledger.records: orphan public verification record for ${providerId}`);
}

if (!process.exitCode) console.log(`Public provider data contract passed: ${providerIds.size} providers, ${recordsByProvider.size} ledger records.`);
