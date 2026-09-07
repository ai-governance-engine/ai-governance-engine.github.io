"""
UAIG 21 CFR Part 11 Audit Trail Integrity Tests
Verifies forward SHA-256 hash chaining and tamper-detection mechanics.
"""
import unittest
import sqlite3
import os
from uaig_core.models import SystemContext, LLMToolPayload, VerificationDecision
from uaig_core.audit_ledger import CFR21AuditLedger

class TestAuditLedgerIntegrity(unittest.TestCase):
    def setUp(self):
        import uuid
        self.test_db = f"test_audit_ledger_{uuid.uuid4().hex[:8]}.db"
        self.ledger = CFR21AuditLedger(db_path=self.test_db)

    def tearDown(self):
        try:
            if os.path.exists(self.test_db):
                os.remove(self.test_db)
        except OSError:
            pass

    def test_AUDIT_01_hash_chain_continuation(self):
        ctx = SystemContext(session_id="S1", user_id="u1", user_clearance=1, max_transaction=100.0, user_is_clinical=False)
        pld = LLMToolPayload(action_name="act1", required_clearance=1, transaction_amount=50.0, is_phi_data=False)
        dec = VerificationDecision(is_authorized=True, status="SAT", elapsed_ms=1.2, diagnostic_message="OK", violating_rules=[])

        h1 = self.ledger.commit_record(ctx, pld, dec)
        self.assertEqual(len(h1), 64)

        h2 = self.ledger.commit_record(ctx, pld, dec)
        self.assertNotEqual(h1, h2)

        is_valid, count, msg = self.ledger.verify_ledger_integrity()
        self.assertTrue(is_valid)
        self.assertEqual(count, 2)

    def test_AUDIT_02_tamper_detection(self):
        ctx = SystemContext(session_id="S1", user_id="u1", user_clearance=1, max_transaction=100.0, user_is_clinical=False)
        pld = LLMToolPayload(action_name="act1", required_clearance=1, transaction_amount=50.0, is_phi_data=False)
        dec = VerificationDecision(is_authorized=True, status="SAT", elapsed_ms=1.2, diagnostic_message="OK", violating_rules=[])

        self.ledger.commit_record(ctx, pld, dec)
        self.ledger.commit_record(ctx, pld, dec)
        self.ledger.commit_record(ctx, pld, dec)

        # Direct database tampering bypass (simulating malicious database administrator)
        with sqlite3.connect(self.test_db) as conn:
            # Disable trigger temporarily to test detection logic
            conn.execute("DROP TRIGGER IF EXISTS prevent_audit_update;")
            conn.execute("UPDATE audit_records SET payload_json = '{\"tampered\": true}' WHERE record_id = 2;")
            conn.commit()

        is_valid, bad_id, msg = self.ledger.verify_ledger_integrity()
        self.assertFalse(is_valid, "Tampered record failed to be detected by cryptographic hash verification.")
        self.assertEqual(bad_id, 2)

if __name__ == "__main__":
    unittest.main()
