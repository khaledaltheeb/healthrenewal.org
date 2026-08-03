import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDLER = ROOT / 'specialists-partners/backend/src/application-review-v6.js'
ENTRY = ROOT / 'specialists-partners/backend/src/index-v4.js'
MIGRATION = ROOT / 'specialists-partners/backend/migrations/0005_signed_application_reviews.sql'
DEPLOY = ROOT / '.github/workflows/deploy-specialists-signed-review-v6.yml'


class SignedApplicationReviewV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handler = HANDLER.read_text(encoding='utf-8')
        cls.entry = ENTRY.read_text(encoding='utf-8')
        cls.migration = MIGRATION.read_text(encoding='utf-8')
        cls.deploy = DEPLOY.read_text(encoding='utf-8') if DEPLOY.exists() else ''

    def test_get_is_view_only_and_post_is_explicit(self):
        self.assertIn("request.method === 'GET'", self.handler)
        self.assertIn("request.method === 'POST'", self.handler)
        self.assertIn("effect:'view_only'", self.handler)
        get_block = self.handler.split('async function handleReviewGet', 1)[1].split('async function handleReviewPost', 1)[0]
        self.assertNotRegex(
            get_block,
            r"UPDATE applications\s+SET status",
            'GET must never approve, reject, or otherwise change application status',
        )
        self.assertIn("form.get('confirm') !== '1'", self.handler)
        self.assertIn("['approved','rejected']", self.handler)

    def test_link_is_signed_limited_and_not_a_bearer_post(self):
        self.assertIn("{name:'HMAC', hash:'SHA-256'}", self.handler)
        self.assertIn('REVIEW_LINK_SECRET', self.handler)
        self.assertIn('REVIEW_LINK_TTL_MINUTES', self.handler)
        self.assertRegex(self.handler, r"payload\.exp <= Math\.floor\(Date\.now\(\) / 1000\)")
        self.assertIn('token_hash TEXT NOT NULL UNIQUE', self.migration)
        self.assertIn('expires_at TEXT NOT NULL', self.migration)

    def test_scanner_open_cannot_consume_decision(self):
        get_block = self.handler.split('async function handleReviewGet', 1)[1].split('async function handleReviewPost', 1)[0]
        self.assertNotIn('used_at =', get_block)
        self.assertNotIn('decision =', get_block)
        self.assertIn('status:303', get_block)
        self.assertIn("cleanUrl.search = ''", get_block)

    def test_csrf_cookie_origin_and_session_controls(self):
        for expected in (
            'HttpOnly', 'SameSite=Strict', 'Secure', 'review_session_hash', 'csrf_hash',
            'enforceSameOrigin(request)', "origin !== expected", "csrf_mismatch",
        ):
            self.assertIn(expected, self.handler + self.migration)
        self.assertIn("content-security-policy", self.handler)
        self.assertIn("form-action 'self'", self.handler)
        self.assertIn("referrer-policy':'no-referrer'", self.handler)

    def test_one_time_atomic_decision_and_audit(self):
        self.assertIn('env.DB.batch([', self.handler)
        self.assertRegex(self.handler, r"SET used_at = \?, decision = \?, decided_by = \?")
        self.assertIn('used_at IS NULL AND revoked_at IS NULL AND expires_at > ?', self.handler)
        self.assertIn("'application_review_decided'", self.handler)
        self.assertIn('review_token_already_used', self.handler)
        self.assertIn("review_session_hash = NULL, csrf_hash = NULL", self.handler)

    def test_page_excludes_private_contact_and_documents(self):
        render_block = self.handler.split('function renderReviewPage', 1)[1].split('function renderResultPage', 1)[0]
        forbidden = ('privateEmail', 'phone', 'whatsapp', 'document', 'credentialUrl', 'certificate')
        for value in forbidden:
            self.assertNotIn(value, render_block)
        for allowed in ('display_name', 'entity_type', 'specialties', 'region'):
            self.assertIn(allowed, render_block)

    def test_rejection_requires_reason_and_owner_can_later_correct(self):
        self.assertIn("cleanString(form.get('reason'), 800, decision === 'rejected')", self.handler)
        self.assertIn('يمكن تعديل الحالة لاحقًا أو تعليق الملف من لوحة الإدارة', self.handler)

    def test_worker_wires_only_new_application_success(self):
        self.assertIn("import baseWorker from './index-v3.js'", self.entry)
        self.assertIn("baseResponse.status !== 201", self.entry)
        self.assertIn('issueApplicationReviewInvitation', self.entry)
        self.assertIn("version:BUILD_VERSION", self.entry)
        self.assertIn("const BUILD_VERSION = '6.0.0'", self.entry)

    def test_migration_applies_to_sqlite(self):
        connection = sqlite3.connect(':memory:')
        connection.executescript('CREATE TABLE applications (id TEXT PRIMARY KEY);')
        connection.executescript(self.migration)
        columns = {row[1] for row in connection.execute("PRAGMA table_info('application_review_invitations')")}
        required = {
            'id', 'application_id', 'token_hash', 'review_session_hash', 'csrf_hash',
            'expires_at', 'used_at', 'revoked_at', 'decision', 'decided_by',
        }
        self.assertTrue(required.issubset(columns), required - columns)

    def test_deployment_contract_requires_worker_secret_name_and_live_health(self):
        for expected in (
            'src/index-v4.js', '0005_signed_application_reviews.sql',
            "'REVIEW_LINK_SECRET'", 'Missing required Worker secret names',
            "health['version'] == '6.0.0'", "'signedReviews'", "'signedReviewSchema'",
        ):
            self.assertIn(expected, self.deploy)
        self.assertIn('/workers/scripts/${WORKER_NAME}/secrets', self.deploy)
        self.assertNotIn('SPECIALISTS_REVIEW_LINK_SECRET', self.deploy)
        self.assertNotIn('REVIEW_LINK_SECRET: ${{ secrets.', self.deploy)
        self.assertNotIn('--secrets-file', self.deploy)


if __name__ == '__main__':
    unittest.main()
