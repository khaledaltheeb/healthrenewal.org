PRAGMA foreign_keys = ON;

-- Any provider who cannot receive notifications must not be offered for new conversations.
UPDATE providers_private
SET accepts_new_requests = 0, updated_at = CURRENT_TIMESTAMP
WHERE notification_enabled <> 1 AND accepts_new_requests = 1;

CREATE TABLE IF NOT EXISTS message_requests (
  request_key_hash TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  sender_role TEXT NOT NULL CHECK (sender_role IN ('visitor','specialist')),
  message_id TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_message_requests_conversation_time
  ON message_requests(conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_email_events_template_time
  ON email_events(template, created_at);
