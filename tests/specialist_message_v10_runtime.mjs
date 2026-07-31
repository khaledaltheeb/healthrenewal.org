import assert from 'node:assert/strict';
import {
  handleSpecialistMessageV10,
  specialistMessageHealth
} from '../specialists-partners/account-backend/src/specialist-message-v10.js';

class FakeStatement {
  constructor(db, sql) {
    this.db = db;
    this.sql = String(sql);
    this.args = [];
  }

  bind(...args) {
    this.args = args;
    return this;
  }

  async first() {
    const sql = this.sql.replace(/\s+/g, ' ').trim();
    if (sql.includes("SELECT provider_id,status FROM providers_private")) {
      return {provider_id: this.db.providerId, status: 'active'};
    }
    if (sql.includes('SELECT count FROM rate_limits')) return {count: 1};
    if (sql.includes('FROM specialist_message_requests')) return null;
    if (sql.includes('SELECT id,reference_id,provider_id,visitor_email,status')) {
      return {
        id: this.db.conversationId,
        reference_id: 'REF-TEST-001',
        provider_id: this.db.providerId,
        visitor_email: 'visitor@example.com',
        status: 'open'
      };
    }
    if (sql.includes('SELECT status FROM conversations')) {
      return {status: this.db.currentStatus};
    }
    if (sql.includes("pragma_table_info('specialist_message_outbox')")) {
      return {count: 17};
    }
    throw new Error(`Unhandled first(): ${sql}`);
  }

  async run() {
    return {meta: {changes: 1}};
  }

  async all() {
    return {results: []};
  }
}

class FakeDB {
  constructor({commitChanges = 1, currentStatus = 'open'} = {}) {
    this.providerId = 'provider-123';
    this.conversationId = 'conversation-123';
    this.commitChanges = commitChanges;
    this.currentStatus = currentStatus;
    this.batches = [];
  }

  prepare(sql) {
    return new FakeStatement(this, sql);
  }

  async batch(statements) {
    this.batches.push(statements);
    return statements.map((_, index) => ({meta: {changes: index === 0 ? this.commitChanges : 1}}));
  }
}

function environment(db) {
  return {
    DB: db,
    RATE_LIMIT_SALT: 'rate-limit-salt-for-runtime-test-0000000000000000',
    OUTBOX_ENCRYPTION_KEY: 'outbox-encryption-key-for-runtime-test-000000000000',
    PORTAL_BASE_URL: 'https://example.com/specialists-partners/portal/'
  };
}

function request(idempotencyKey) {
  return new Request('https://worker.example/v1/specialist/conversations/conversation-123/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'idempotency-key': idempotencyKey,
      'cf-connecting-ip': '203.0.113.10'
    },
    body: JSON.stringify({body: 'رد اختباري آمن'})
  });
}

const actor = {id: 'user-123', provider_id: 'provider-123'};
let fetchCalls = 0;
globalThis.fetch = async () => {
  fetchCalls += 1;
  throw new Error('Network delivery must not occur before the durable transaction commits.');
};

{
  const db = new FakeDB({commitChanges: 0, currentStatus: 'closed'});
  const response = await handleSpecialistMessageV10(
    request('reply-race-000001'),
    environment(db),
    {},
    {},
    actor,
    db.conversationId
  );
  const payload = await response.json();
  assert.equal(response.status, 409);
  assert.equal(payload.error, 'conversation_closed');
  assert.equal(fetchCalls, 0);
  assert.equal(db.batches.length, 1);

  const transactionSql = db.batches[0].map(statement => statement.sql).join('\n');
  for (const contract of [
    'INSERT INTO messages',
    "status='open'",
    'INSERT INTO specialist_message_requests',
    'INSERT INTO conversation_tokens',
    'INSERT INTO specialist_message_outbox',
    'INSERT INTO identity_audit_log'
  ]) {
    assert.ok(transactionSql.includes(contract), `Missing atomic contract: ${contract}`);
  }
}

{
  const db = new FakeDB({commitChanges: 1, currentStatus: 'open'});
  const response = await handleSpecialistMessageV10(
    request('reply-success-0001'),
    environment(db),
    {},
    {},
    actor,
    db.conversationId
  );
  const payload = await response.json();
  assert.equal(response.status, 201);
  assert.equal(payload.ok, true);
  assert.equal(payload.visitorAccessIssued, true);
  assert.equal(payload.notificationQueued, true);
  assert.equal(fetchCalls, 0);
  assert.equal(db.batches.length, 1);
}

{
  const db = new FakeDB();
  const health = await specialistMessageHealth(environment(db));
  assert.deepEqual(health, {
    specialistReplyLink: true,
    messageOutboxSchema: true,
    messageOutboxEncryption: true
  });
}

console.log('specialist_message_v10_runtime: ok');
