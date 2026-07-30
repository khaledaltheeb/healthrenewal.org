PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS identity_users (
  id TEXT PRIMARY KEY,
  provider_id TEXT UNIQUE,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  phone_e164 TEXT,
  display_name_ar TEXT NOT NULL,
  display_name_en TEXT,
  role TEXT NOT NULL DEFAULT 'specialist'
    CHECK (role IN ('owner','admin','reviewer','moderator','specialist')),
  status TEXT NOT NULL DEFAULT 'invited'
    CHECK (status IN ('invited','active','suspended','archived')),
  password_hash TEXT,
  password_salt TEXT,
  password_iterations INTEGER,
  password_set_at TEXT,
  must_change_password INTEGER NOT NULL DEFAULT 1 CHECK (must_change_password IN (0,1)),
  verified_at TEXT,
  email_verified_at TEXT,
  phone_verified_at TEXT,
  email_notifications INTEGER NOT NULL DEFAULT 1 CHECK (email_notifications IN (0,1)),
  new_message_notifications INTEGER NOT NULL DEFAULT 1 CHECK (new_message_notifications IN (0,1)),
  failed_login_count INTEGER NOT NULL DEFAULT 0,
  locked_until TEXT,
  last_login_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_identity_users_email ON identity_users(lower(email));
CREATE INDEX IF NOT EXISTS idx_identity_users_role_status ON identity_users(role, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_identity_users_provider ON identity_users(provider_id);

CREATE TABLE IF NOT EXISTS identity_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  ip_hash TEXT NOT NULL,
  user_agent_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES identity_users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_identity_sessions_active
  ON identity_sessions(token_hash, expires_at, revoked_at);
CREATE INDEX IF NOT EXISTS idx_identity_sessions_user
  ON identity_sessions(user_id, last_used_at DESC);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  purpose TEXT NOT NULL CHECK (purpose IN ('setup','reset','admin_reset')),
  expires_at TEXT NOT NULL,
  used_at TEXT,
  requested_by_user_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES identity_users(id) ON DELETE CASCADE,
  FOREIGN KEY (requested_by_user_id) REFERENCES identity_users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_active
  ON password_reset_tokens(token_hash, expires_at, used_at);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user
  ON password_reset_tokens(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS provider_account_drafts (
  provider_id TEXT PRIMARY KEY,
  draft_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','submitted','approved','rejected')),
  review_notes TEXT NOT NULL DEFAULT '',
  submitted_at TEXT,
  reviewed_at TEXT,
  reviewed_by_user_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE,
  FOREIGN KEY (reviewed_by_user_id) REFERENCES identity_users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_provider_account_drafts_status
  ON provider_account_drafts(status, updated_at DESC);

CREATE TABLE IF NOT EXISTS identity_audit_log (
  id TEXT PRIMARY KEY,
  actor_user_id TEXT,
  event_type TEXT NOT NULL,
  target_user_id TEXT,
  entity_id TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (actor_user_id) REFERENCES identity_users(id) ON DELETE SET NULL,
  FOREIGN KEY (target_user_id) REFERENCES identity_users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_identity_audit_time ON identity_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_identity_audit_actor ON identity_audit_log(actor_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_identity_audit_target ON identity_audit_log(target_user_id, created_at DESC);
