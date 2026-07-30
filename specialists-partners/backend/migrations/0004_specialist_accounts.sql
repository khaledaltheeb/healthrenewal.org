PRAGMA foreign_keys = ON;

ALTER TABLE providers_private
  ADD COLUMN account_enabled INTEGER NOT NULL DEFAULT 1
  CHECK (account_enabled IN (0,1));

ALTER TABLE providers_private
  ADD COLUMN account_last_login_at TEXT;

-- Passwordless login links are one-time and short-lived. Only hashes are stored.
CREATE TABLE IF NOT EXISTS specialist_login_tokens (
  id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  used_at TEXT,
  request_ip_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_specialist_login_tokens_active
  ON specialist_login_tokens(token_hash, expires_at, used_at);

CREATE INDEX IF NOT EXISTS idx_specialist_login_tokens_provider
  ON specialist_login_tokens(provider_id, created_at DESC);

-- Browser sessions are intentionally short-lived and revocable. Raw bearer tokens
-- never enter D1; only SHA-256 hashes are persisted.
CREATE TABLE IF NOT EXISTS specialist_sessions (
  id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_specialist_sessions_active
  ON specialist_sessions(token_hash, expires_at, revoked_at);

CREATE INDEX IF NOT EXISTS idx_specialist_sessions_provider
  ON specialist_sessions(provider_id, last_used_at DESC);

-- Idempotency records prevent duplicate replies when the browser retries a request.
CREATE TABLE IF NOT EXISTS specialist_message_requests (
  idempotency_key TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_specialist_message_requests_provider
  ON specialist_message_requests(provider_id, created_at DESC);
