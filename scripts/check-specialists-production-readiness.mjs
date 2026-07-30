#!/usr/bin/env node

const required = [
  'CLOUDFLARE_API_TOKEN',
  'CLOUDFLARE_ACCOUNT_ID',
  'SPECIALISTS_D1_DATABASE_ID',
  'RESEND_API_KEY',
  'TURNSTILE_SECRET',
  'SPECIALISTS_ADMIN_API_KEY',
  'SPECIALISTS_RATE_LIMIT_SALT',
  'SPECIALISTS_REVIEW_LINK_SECRET',
  'SPECIALISTS_FROM_EMAIL',
  'SPECIALISTS_OWNER_EMAIL',
];

const optional = [
  'SPECIALISTS_REVIEWER_API_KEY',
  'SPECIALISTS_MODERATOR_API_KEY',
];

const errors = [];
const warnings = [];
const value = (name) => String(process.env[name] || '').trim();

for (const name of required) {
  if (!value(name)) errors.push(`${name}: missing`);
}

const minLength = (name, length) => {
  if (value(name) && value(name).length < length) {
    errors.push(`${name}: must be at least ${length} characters`);
  }
};

for (const name of [
  'SPECIALISTS_ADMIN_API_KEY',
  'SPECIALISTS_RATE_LIMIT_SALT',
  'SPECIALISTS_REVIEW_LINK_SECRET',
]) minLength(name, 32);

for (const name of optional) {
  if (value(name)) minLength(name, 32);
}

const mailboxPattern = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;
const namedMailboxPattern = /^.{1,100}\s<([^\s@<>]+@[^\s@<>]+\.[^\s@<>]+)>$/;
const validMailbox = (candidate, allowDisplayName = false) =>
  mailboxPattern.test(candidate) || (allowDisplayName && namedMailboxPattern.test(candidate));

if (value('SPECIALISTS_OWNER_EMAIL') && !validMailbox(value('SPECIALISTS_OWNER_EMAIL'))) {
  errors.push('SPECIALISTS_OWNER_EMAIL: invalid mailbox format');
}
if (value('SPECIALISTS_FROM_EMAIL') && !validMailbox(value('SPECIALISTS_FROM_EMAIL'), true)) {
  errors.push('SPECIALISTS_FROM_EMAIL: use mailbox@example.org or Display Name <mailbox@example.org>');
}
if (value('SPECIALISTS_FROM_EMAIL') && mailboxPattern.test(value('SPECIALISTS_FROM_EMAIL'))) {
  warnings.push('SPECIALISTS_FROM_EMAIL: plain mailbox accepted; a verified sender name is recommended');
}

if (value('CLOUDFLARE_ACCOUNT_ID') && !/^[a-f0-9]{32}$/i.test(value('CLOUDFLARE_ACCOUNT_ID'))) {
  errors.push('CLOUDFLARE_ACCOUNT_ID: expected 32 hexadecimal characters');
}

if (value('SPECIALISTS_D1_DATABASE_ID') && !/^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value('SPECIALISTS_D1_DATABASE_ID'))) {
  errors.push('SPECIALISTS_D1_DATABASE_ID: expected UUID format');
}

const secretNames = [
  'SPECIALISTS_ADMIN_API_KEY',
  'SPECIALISTS_REVIEWER_API_KEY',
  'SPECIALISTS_MODERATOR_API_KEY',
  'SPECIALISTS_RATE_LIMIT_SALT',
  'SPECIALISTS_REVIEW_LINK_SECRET',
].filter((name) => value(name));

for (let i = 0; i < secretNames.length; i += 1) {
  for (let j = i + 1; j < secretNames.length; j += 1) {
    if (value(secretNames[i]) === value(secretNames[j])) {
      errors.push(`${secretNames[i]} and ${secretNames[j]} must be different`);
    }
  }
}

for (const name of required.concat(optional)) {
  const candidate = value(name);
  if (!candidate) continue;
  if (/^(changeme|example|test|secret|password|todo|replace[-_ ]?me)$/i.test(candidate)) {
    errors.push(`${name}: placeholder value is not allowed`);
  }
  if (/\s/.test(candidate) && !name.endsWith('_EMAIL')) {
    errors.push(`${name}: whitespace is not allowed`);
  }
}

const summary = {
  ok: errors.length === 0,
  requiredConfigured: required.filter((name) => value(name)).length,
  requiredTotal: required.length,
  optionalConfigured: optional.filter((name) => value(name)).length,
  optionalTotal: optional.length,
  warnings,
  errors,
};

console.log(JSON.stringify(summary, null, 2));
if (!summary.ok) process.exit(1);
