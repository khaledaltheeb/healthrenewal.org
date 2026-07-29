#!/usr/bin/env node

import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile('specialists-partners/assets/safe-preview.js', 'utf8');
const joinPage = await readFile('specialists-partners/join.html', 'utf8');

const listeners = new Map();
const elements = new Map();

function element(id, value = '') {
  const node = {
    id,
    value,
    checked: false,
    hidden: true,
    dataset: {},
    selectedOptions: [],
    addEventListener(type, handler) {
      listeners.set(`${id}:${type}`, handler);
    },
    reportValidity() {
      return true;
    },
    focus() {},
    select() {}
  };
  elements.set(id, node);
  return node;
}

const values = {
  entityType: 'specialist',
  displayName: 'اسم مهني تجريبي',
  professionalTitle: 'اختصاصي',
  centerType: '',
  services: 'تقييم، تدريب',
  languages: 'العربية، الإنجليزية',
  country: 'الأردن',
  governorate: 'عمّان',
  city: 'عمّان',
  area: 'الشميساني',
  serviceAreas: 'عمّان',
  qualification: 'ماجستير',
  institution: 'جامعة تجريبية',
  qualificationLevel: 'ماجستير',
  qualificationYear: '2020',
  licenseAuthority: 'جهة مهنية',
  licenseStatus: 'pending_review',
  licenseIdentifier: 'LICENSE-SENSITIVE-987654',
  experienceYears: '7',
  currentRole: 'مقدم خدمة',
  shortBio: 'نبذة مهنية عامة',
  availability: 'available',
  typicalResponse: 'خلال يومي عمل',
  officialProfile: 'https://example.org/profile',
  website: 'https://example.org',
  privateEmail: 'private@example.org',
  privatePhone: '+962799999999',
  'cf-turnstile-response': 'turnstile-secret-token'
};

for (const [id, value] of Object.entries(values)) element(id, value);
for (const id of ['output', 'form-status', 'preview-record', 'copy-output', 'download-output', 'submit-application']) element(id);

const form = element('onboarding-form');
for (const id of ['acceptsInternalMessages', 'acceptsNewRequests', 'showPhone', 'showEmail', 'showOfficialProfile']) {
  element(id).checked = true;
}

for (const [id, options] of Object.entries({
  specialties: ['علاج وظيفي'],
  ageGroups: ['الأطفال'],
  serviceModes: ['حضوري'],
  collaborationInterests: ['مراجعة المحتوى']
})) {
  const node = elements.get(id) || element(id);
  node.selectedOptions = options.map(value => ({ value }));
}

const documentListeners = new Map();
const document = {
  body: { dataset: { page: 'join' } },
  getElementById(id) {
    return elements.get(id) || null;
  },
  addEventListener(type, handler) {
    documentListeners.set(type, handler);
  },
  execCommand() {
    return true;
  },
  createElement() {
    return { click() {}, rel: '', href: '', download: '' };
  }
};

const sandbox = {
  document,
  window: { setTimeout: fn => fn() },
  navigator: { clipboard: { writeText: async () => {} } },
  Blob,
  URL: {
    createObjectURL: () => 'blob:test',
    revokeObjectURL() {}
  },
  console
};

vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: 'safe-preview.js' });
documentListeners.get('DOMContentLoaded')?.();

const click = listeners.get('preview-record:click');
assert.equal(typeof click, 'function', 'يجب ربط زر المعاينة بطبقة التنقيح');
click({ stopImmediatePropagation() {} });

const output = elements.get('output').value;
assert.ok(output, 'يجب إنشاء سجل مراجعة');
const record = JSON.parse(output);
const serialized = JSON.stringify(record);

for (const forbidden of [
  'privateEmail',
  'privatePhone',
  'phone',
  'turnstileToken',
  'cf-turnstile-response',
  'licenseIdentifier',
  'publicIdentifier',
  'private@example.org',
  '+962799999999',
  'turnstile-secret-token',
  'LICENSE-SENSITIVE-987654'
]) {
  assert.equal(serialized.includes(forbidden), false, `تسرّب حقل أو قيمة محظورة: ${forbidden}`);
}

assert.equal(record.recordType, 'specialist_application_public_review');
assert.equal(record.displayName, 'اسم مهني تجريبي');
assert.equal(record.publicContactPreferences.showEmail, true);
assert.equal(record.publicContactPreferences.showPhone, true);
assert.equal(record.publicContactPreferences.officialProfile, 'https://example.org/profile');
assert.equal(record.publicContactPreferences.website, 'https://example.org');
assert.equal(Object.hasOwn(record.licenses[0], 'publicIdentifier'), false, 'يجب ألا يتضمن السجل العام رقم الترخيص');
assert.match(record.privacyNotice, /أرقام الترخيص/, 'يجب أن يوضح إشعار الخصوصية استبعاد أرقام الترخيص');

// لا تُصدر روابط غير آمنة قد تتحول لاحقًا إلى href قابل للتنفيذ داخل ملف عام.
elements.get('officialProfile').value = 'javascript:alert(document.domain)';
elements.get('website').value = 'data:text/html,<script>alert(1)</script>';
click({ stopImmediatePropagation() {} });
const unsafeRecord = JSON.parse(elements.get('output').value);
assert.equal(unsafeRecord.publicContactPreferences.officialProfile, null, 'يجب رفض بروتوكول javascript:');
assert.equal(unsafeRecord.publicContactPreferences.website, null, 'يجب رفض بروتوكول data:');

// حتى الرابط الآمن لا يخرج في النسخة العامة دون موافقة صريحة على عرضه.
elements.get('officialProfile').value = 'https://example.org/private-profile';
elements.get('showOfficialProfile').checked = false;
click({ stopImmediatePropagation() {} });
const consentRecord = JSON.parse(elements.get('output').value);
assert.equal(consentRecord.publicContactPreferences.showOfficialProfile, false);
assert.equal(consentRecord.publicContactPreferences.officialProfile, null, 'يجب ربط نشر الملف الرسمي بالموافقة الصريحة');

assert.match(joinPage, /assets\/safe-preview\.js\?v=/, 'يجب تحميل طبقة التنقيح في صفحة الانضمام');
assert.ok(joinPage.indexOf('assets/forms.js') < joinPage.indexOf('assets/safe-preview.js'), 'يجب تحميل طبقة التنقيح بعد منطق النموذج الأساسي');

console.log('Specialist safe-preview security regression test passed.');