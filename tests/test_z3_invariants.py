"""
UAIG Formal Invariant Tests
Evaluates Z3 SMT boundary conditions, soundness, and completeness.
"""
import unittest
from uaig_core.models import SystemContext, LLMToolPayload
from uaig_core.z3_engine import Z3FormalVerificationEngine

class TestZ3FormalInvariants(unittest.TestCase):
    def setUp(self):
        self.engine = Z3FormalVerificationEngine(timeout_ms=500)
        self.base_context = SystemContext(
            session_id="SESS-VAL-001",
            user_id="user_admin_01",
            user_clearance=3,
            max_transaction=5000.0,
            user_is_clinical=False
        )

    def test_INV_01_compliant_transaction(self):
        payload = LLMToolPayload(
            action_name="dispatch_payment",
            required_clearance=2,
            transaction_amount=2500.0,
            is_phi_data=False
        )
        dec = self.engine.evaluate(self.base_context, payload)
        self.assertTrue(dec.is_authorized)
        self.assertEqual(dec.status, "SAT")
        self.assertEqual(len(dec.violating_rules), 0)

    def test_INV_02_exact_boundary_transaction(self):
        payload = LLMToolPayload(
            action_name="dispatch_payment",
            required_clearance=3,
            transaction_amount=5000.0,
            is_phi_data=False
        )
        dec = self.engine.evaluate(self.base_context, payload)
        self.assertTrue(dec.is_authorized)
        self.assertEqual(dec.status, "SAT")

    def test_INV_03_financial_overage_refutation(self):
        payload = LLMToolPayload(
            action_name="dispatch_payment",
            required_clearance=1,
            transaction_amount=5000.01,
            is_phi_data=False
        )
        dec = self.engine.evaluate(self.base_context, payload)
        self.assertFalse(dec.is_authorized)
        self.assertEqual(dec.status, "UNSAT")
        self.assertIn("POL-FIN-001", dec.violating_rules)

    def test_INV_04_clearance_escalation_refutation(self):
        payload = LLMToolPayload(
            action_name="elevated_admin_exec",
            required_clearance=4,
            transaction_amount=0.0,
            is_phi_data=False
        )
        dec = self.engine.evaluate(self.base_context, payload)
        self.assertFalse(dec.is_authorized)
        self.assertEqual(dec.status, "UNSAT")
        self.assertIn("POL-SEC-001", dec.violating_rules)

    def test_INV_05_phi_unauthorized_access_refutation(self):
        payload = LLMToolPayload(
            action_name="query_patient_records",
            required_clearance=1,
            transaction_amount=0.0,
            is_phi_data=True
        )
        dec = self.engine.evaluate(self.base_context, payload)
        self.assertFalse(dec.is_authorized)
        self.assertEqual(dec.status, "UNSAT")
        self.assertIn("POL-REG-001", dec.violating_rules)

    def test_INV_06_phi_clinical_authorized(self):
        clinical_context = SystemContext(
            session_id="SESS-CLI-001",
            user_id="dr_smith",
            user_clearance=3,
            max_transaction=1000.0,
            user_is_clinical=True
        )
        payload = LLMToolPayload(
            action_name="query_patient_records",
            required_clearance=2,
            transaction_amount=0.0,
            is_phi_data=True
        )
        dec = self.engine.evaluate(clinical_context, payload)
        self.assertTrue(dec.is_authorized)
        self.assertEqual(dec.status, "SAT")

    def test_INV_07_compound_adversarial_hallucination(self):
        # Violates all three invariants simultaneously
        payload = LLMToolPayload(
            action_name="exfiltrate_and_drain",
            required_clearance=5,
            transaction_amount=999999.0,
            is_phi_data=True
        )
        dec = self.engine.evaluate(self.base_context, payload)
        self.assertFalse(dec.is_authorized)
        self.assertEqual(dec.status, "UNSAT")
        self.assertTrue(len(dec.violating_rules) >= 1)

if __name__ == "__main__":
    unittest.main()
