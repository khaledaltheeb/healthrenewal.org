PRAGMA foreign_keys = ON;

ALTER TABLE providers_private
  ADD COLUMN accepts_new_requests INTEGER NOT NULL DEFAULT 1
  CHECK (accepts_new_requests IN (0,1));

ALTER TABLE applications
  ADD COLUMN admin_notes TEXT NOT NULL DEFAULT '';

ALTER TABLE applications
  ADD COLUMN reviewed_at TEXT;

ALTER TABLE applications
  ADD COLUMN reviewed_by TEXT;

ALTER TABLE conversations
  ADD COLUMN admin_notes TEXT NOT NULL DEFAULT '';

ALTER TABLE conversations
  ADD COLUMN closed_by TEXT;

CREATE TABLE IF NOT EXISTS email_events (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  recipient_hash TEXT NOT NULL,
  template TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('sent','failed','skipped')),
  provider_message_id TEXT,
  error_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_events_entity_time
  ON email_events(entity_type, entity_id, created_at);

CREATE INDEX IF NOT EXISTS idx_email_events_status_time
  ON email_events(status, created_at);

CREATE INDEX IF NOT EXISTS idx_applications_review_status
  ON applications(status, reviewed_at);

CREATE INDEX IF NOT EXISTS idx_conversations_status_updated
  ON conversations(status, updated_at);
