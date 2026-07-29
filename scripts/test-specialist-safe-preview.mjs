#!/usr/bin/env node

import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { URL as NodeURL } from 'node:url';
import vm from 'node:vm';

const source = await readFile('specialists-partners/assets/safe-preview.js', 'utf8');
const joinPage = await readFile('specialists-partners/join.html', 'utf8');
const listeners = new Map();
const elements = new Map();

function element(id, value = '') {
  const node = {
    id, value, checked: false, hidden: true, dataset: {}, selectedOptions: [],
    addEventListener(type, handler) { listeners.set(`${id}:${type}`, handler); },
    reportValidity() { return true; }, focus() {}, select() {}
  };
  elements.set(id, node);
  return node;
}

const values = {
  entityType: 'professional', displayName: 'اسم مهني تجريبي', professionalTitle: 'اختصاصي', centerType: '',
  services: 'تقييم، تدريب', languages: 'العربية، الإنجليزية', country: 'الأردن', governorate: 'عمّان', city: 'عمّان', area: 'الشميساني', serviceAreas: 'عمّان',
  qualification: 'ماجستير', institution: 'جامعة تجريبية', qualificationLevel: 'ماجستير', qualificationYear: '2020',
  licenseAuthority: 'جهة مهنية', licenseStatus: 'approved', licenseIdentifier: 'LICENSE-SENSITIVE-987654', experienceYears: '7', currentRole: 'مقدم خدمة',
  shortBio: 'نبذة مهنية عامة', availability: 'available', typicalResponse: 'خلال يومي عمل', officialProfile: 'https://example.org/profile', website: 'https://example.org',
  privateEmail: 'private@example.org', privatePhone: '+962799999999', 'cf-turnstile-response': 'turnstile-secret-token'
};
for (const [id, value] of Object.entries(values)) element(id, value);
for (const id of ['output', 'form-status', 'preview-record', 'copy-output', 'download-output', 'submit-application']) element(id);
element('onboarding-form');
for (const id of ['acceptsInternalMessages', 'acceptsNewRequests', 'showPhone', 'showEmail', 'showOfficialProfile']) element(id).checked = true;
for (const [id, options] of Object.entries({specialties:['علاج وظيفي'], ageGroups:['الأطفال'], serviceModes:['حضوري'], collaborationInterests:['مراجعة المحتوى']})) {
  const node = elements.get(id) || element(id);
  node.selectedOptions = options.map(value => ({value}));
}

const documentListeners = new Map();
const document = {
  body: {dataset: {page: 'join'}},
  getElementById: id => elements.get(id) || null,
  addEventListener: (type, handler) => documentListeners.set(type, handler),
  execCommand: () => true,
  createElement: () => ({click() {}, rel: '', href: '', download: ''})
};
NodeURL.createObjectURL = () => 'blob:test';
NodeURL.revokeObjectURL = () => {};
const sandbox = {document, window:{setTimeout: fn => fn()}, navigator:{clipboard:{writeText: async () => {}}}, Blob, URL:NodeURL, console};
vm.createContext(sandbox);
vm.runInContext(source, sandbox, {filename:'safe-preview.js'});
documentListeners.get('DOMContentLoaded')?.();
const click = listeners.get('preview-record:click');
assert.equal(typeof click, 'function');
click({stopImmediatePropagation() {}});
const record = JSON.parse(elements.get('output').value);
const serialized = JSON.stringify(record);
for (const forbidden of ['privateEmail','privatePhone','phone','turnstileToken','cf-turnstile-response','licenseIdentifier','publicIdentifier','private@example.org','+962799999999','turnstile-secret-token','LICENSE-SENSITIVE-987654','approved']) {
  assert.equal(serialized.includes(forbidden), false, `تسرّب حقل أو قيمة محظورة: ${forbidden}`);
}
assert.equal(record.applicationStatus, 'new');
assert.equal(record.licenses[0].status, 'pending_review');
assert.equal(record.publicContactPreferences.officialProfile, 'https://example.org/profile');

elements.get('officialProfile').value = 'javascript:alert(1)';
elements.get('website').value = 'https://user:secret@example.org/';
click({stopImmediatePropagation() {}});
const unsafe = JSON.parse(elements.get('output').value);
assert.equal(unsafe.publicContactPreferences.officialProfile, null);
assert.equal(unsafe.publicContactPreferences.website, null);

assert.match(joinPage, /assets\/safe-preview\.js\?v=/);
assert.ok(joinPage.indexOf('assets/forms.js') < joinPage.indexOf('assets/safe-preview.js'));
console.log('Specialist safe-preview security regression test passed.');
