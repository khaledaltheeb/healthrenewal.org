PRAGMA foreign_keys = ON;

-- Short-lived bearer sessions keep the long-lived owner key out of routine
-- browser requests. Only hashes are stored.
CREATE TABLE IF NOT EXISTS admin_sessions (
  id TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('owner','reviewer','moderator')),
  actor_label TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_sessions_active
  ON admin_sessions(token_hash, expires_at, revoked_at);

-- profile_json is intentionally public-safe. Private notification addresses,
-- evidence documents, and review notes live in separate tables.
CREATE TABLE IF NOT EXISTS provider_profiles (
  provider_id TEXT PRIMARY KEY,
  application_id TEXT,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('professional','center')),
  profile_json TEXT NOT NULL DEFAULT '{}',
  publication_status TEXT NOT NULL DEFAULT 'draft'
    CHECK (publication_status IN ('draft','review','published','suspended','archived')),
  verification_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (verification_status IN ('pending','provisional','verified','rejected','expired')),
  consent_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (consent_status IN ('pending','approved','revoked')),
  reviewer_role TEXT,
  last_verified_at TEXT,
  next_review_at TEXT,
  published_at TEXT,
  public_revision INTEGER NOT NULL DEFAULT 0 CHECK (public_revision >= 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE,
  FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_provider_profiles_publication
  ON provider_profiles(publication_status, verification_status, consent_status, updated_at);

CREATE INDEX IF NOT EXISTS idx_provider_profiles_application
  ON provider_profiles(application_id);

-- This record is private. It stores the decision checklist and evidence counts,
-- but never document images or identity numbers.
CREATE TABLE IF NOT EXISTS provider_review_records (
  provider_id TEXT PRIMARY KEY,
  checklist_json TEXT NOT NULL DEFAULT '{}',
  evidence_summary_json TEXT NOT NULL DEFAULT '{}',
  private_notes TEXT NOT NULL DEFAULT '',
  public_note TEXT NOT NULL DEFAULT '',
  decision TEXT NOT NULL DEFAULT 'pending'
    CHECK (decision IN ('pending','changes_requested','approved','rejected','suspended')),
  reviewer_role TEXT,
  reviewed_at TEXT,
  next_review_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE
);

-- Immutable revisions provide rollback evidence without overwriting history.
CREATE TABLE IF NOT EXISTS provider_profile_versions (
  id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  profile_json TEXT NOT NULL,
  publication_status TEXT NOT NULL,
  actor_role TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (provider_id, revision),
  FOREIGN KEY (provider_id) REFERENCES providers_private(provider_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_provider_profile_versions
  ON provider_profile_versions(provider_id, revision DESC);
