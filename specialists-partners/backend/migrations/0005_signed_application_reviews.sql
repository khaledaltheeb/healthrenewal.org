PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS application_review_invitations (
  id TEXT PRIMARY KEY,
  application_id TEXT NOT NULL,
  reference_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  review_session_hash TEXT,
  csrf_hash TEXT,
  expires_at TEXT NOT NULL,
  opened_at TEXT,
  used_at TEXT,
  revoked_at TEXT,
  decision TEXT CHECK (decision IN ('approved','rejected') OR decision IS NULL),
  decided_by TEXT,
  decision_reason TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_application_review_active
  ON application_review_invitations(application_id, expires_at, used_at, revoked_at);

CREATE INDEX IF NOT EXISTS idx_application_review_session
  ON application_review_invitations(review_session_hash, expires_at);

CREATE INDEX IF NOT EXISTS idx_application_review_expiry
  ON application_review_invitations(expires_at);
