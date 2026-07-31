import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "specialists-partners/account-backend/src/specialist-reply-v10.js"
PRODUCTION = ROOT / "specialists-partners/account-backend/src/index-v10-production.js"


class SpecialistReplyTransactionV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = MODULE.read_text(encoding="utf-8")
        cls.production = PRODUCTION.read_text(encoding="utf-8")

    def test_production_release_contract_does_not_drift(self):
        self.assertIn("const BUILD_VERSION='10.2.0'", self.production)
        self.assertIn("handleSpecialistReply", self.production)
        self.assertNotIn("const BUILD_VERSION='10.2.1'", self.production)

    def test_existing_identity_session_contract_is_reused(self):
        self.assertIn("new URL('/v1/auth/session',request.url)", self.module)
        self.assertIn("finalWorker.fetch(sessionRequest,env,ctx)", self.module)
        self.assertNotIn("FROM identity_sessions", self.module)

    def test_message_commit_is_guarded_by_open_conversation(self):
        self.assertIn("status='open'", self.module)
        self.assertIn("INSERT INTO messages", self.module)
        self.assertIn("INSERT INTO specialist_message_requests", self.module)
        self.assertIn("INSERT INTO identity_audit_log", self.module)
        self.assertIn("env.DB.batch(statements)", self.module)
        self.assertIn("conversation_closed", self.module)
        self.assertIn("meta?.changes", self.module)

    def test_visitor_tokens_are_rotated_and_fragment_only(self):
        self.assertIn("DELETE FROM conversation_tokens WHERE conversation_id=? AND role='visitor'", self.module)
        self.assertIn("INSERT INTO conversation_tokens", self.module)
        self.assertIn("#conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(token)}&role=visitor", self.module)
        self.assertNotIn("?token=", self.module)

    def test_delivery_failure_does_not_turn_committed_reply_into_http_500(self):
        self.assertIn("ctx.waitUntil(deliverVisitorReply", self.module)
        self.assertIn("visitor_reply_email_failed", self.module)
        self.assertIn("for(let attempt=1;attempt<=3;attempt+=1)", self.module)
        self.assertIn("idempotency-key", self.module)


if __name__ == "__main__":
    unittest.main()
