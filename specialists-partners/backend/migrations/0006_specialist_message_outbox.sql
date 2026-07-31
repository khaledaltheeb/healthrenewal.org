PRAGMA foreign_keys = ON;

-- Durable delivery queue for specialist replies. Sensitive link payloads are
-- encrypted by the Worker before they enter D1 and are purged after delivery.
CREATE TABLE IF NOT EXISTS specialist_message_outbox (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL UNIQUE,
  conversation_id TEXT NOT NULL,
  provider_id TEXT NOT NULL,
  conversation_token_id TEXT,
  recipient_email TEXT NOT NULL,
  payload_ciphertext TEXT NOT NULL,
  payload_iv TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued','sending','retry','sent','failed','superseded')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  next_attempt_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  lease_expires_at TEXT,
  provider_message_id TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at TEXT,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE,
  FOREIGN KEY (conversation_token_id) REFERENCES conversation_tokens(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_specialist_message_outbox_due
  ON specialist_message_outbox(status, next_attempt_at, lease_expires_at, created_at);

CREATE INDEX IF NOT EXISTS idx_specialist_message_outbox_conversation
  ON specialist_message_outbox(conversation_id, created_at DESC, status);

CREATE INDEX IF NOT EXISTS idx_specialist_message_outbox_provider
  ON specialist_message_outbox(provider_id, created_at DESC, status);
