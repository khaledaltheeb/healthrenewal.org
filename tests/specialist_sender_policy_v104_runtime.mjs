import assert from 'node:assert/strict';
import worker, {senderReadiness} from '../specialists-partners/account-backend/src/index-v10-production.js';

const missing = senderReadiness({});
assert.equal(missing.ready, false);
assert.equal(missing.code, 'sender_not_configured');

const consumer = senderReadiness({FROM_EMAIL:'منصة الصحة النفسية <pterminology@gmail.com>'});
assert.equal(consumer.ready, false);
assert.equal(consumer.code, 'sender_domain_not_verified');
assert.equal(consumer.domain, 'gmail.com');

const gmail = senderReadiness({FROM_EMAIL:'pterminology@gmail.com'});
assert.equal(gmail.ready, false);
assert.equal(gmail.code, 'sender_domain_not_verified');
assert.equal(gmail.domain, 'gmail.com');

const testSender = senderReadiness({FROM_EMAIL:'onboarding@resend.dev'});
assert.equal(testSender.ready, false);
assert.equal(testSender.code, 'resend_test_sender');

const candidate = senderReadiness({FROM_EMAIL:'accounts@example.org'});
assert.equal(candidate.ready, true);
assert.equal(candidate.code, 'sender_domain_candidate');

const undeclared = senderReadiness({
  FROM_EMAIL:'accounts@example.org',
  RESEND_VERIFIED_SENDER_DOMAINS:'mail.example.org',
});
assert.equal(undeclared.ready, false);
assert.equal(undeclared.code, 'sender_domain_not_declared_verified');

const declared = senderReadiness({
  FROM_EMAIL:'accounts@example.org',
  RESEND_VERIFIED_SENDER_DOMAINS:'example.org, mail.example.org',
});
assert.equal(declared.ready, true);
assert.equal(declared.code, 'sender_domain_declared_verified');

const response = await worker.fetch(
  new Request('https://pterminology-specialist-accounts.example/v1/auth/password/request', {
    method:'POST',
    headers:{origin:'https://healthrenewal.org'},
  }),
  {
    FROM_EMAIL:'pterminology@gmail.com',
    ALLOWED_ORIGINS:'https://healthrenewal.org',
  },
  {waitUntil() {}},
);
assert.equal(response.status, 503);
assert.equal(response.headers.get('access-control-allow-origin'), 'https://healthrenewal.org');
const payload = await response.json();
assert.equal(payload.error, 'email_sender_not_verified');
assert.equal(payload.senderReady, false);
assert.equal(payload.senderCode, 'sender_domain_not_verified');
assert.equal(payload.manualRecoveryAvailable, false);
assert.match(payload.message, /لم يُنشأ أو يُرسل أي رابط/);

console.log('specialist_sender_policy_v104_runtime: ok');
