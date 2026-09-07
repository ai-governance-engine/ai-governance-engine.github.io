import unittest
import json
import os
import hashlib
from datetime import datetime
from uaig_gateway import Z3EnterprisePolicyVerifier

# A globally accessible list to capture test results for the CSA Report Generator
csa_test_results = []

class TestUAIGGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = Z3EnterprisePolicyVerifier()
        cls.context = {
            "user_clearance": 3,          # High clearance
            "max_transaction": 10000.0,   # Absolute enterprise limit
            "user_is_clinical": False     # Non-clinical user (Cannot access PHI)
        }

    def log_result(self, test_name, expected, actual, is_pass, payload, audit_trail):
        csa_test_results.append({
            "test_id": test_name,
            "timestamp": datetime.utcnow().isoformat(),
            "payload_injected": payload,
            "expected_status": expected,
            "actual_status": actual,
            "is_pass": is_pass,
            "audit_trail": audit_trail
        })

    def test_01_valid_low_risk_transaction(self):
        """TC-01: LLM generates a valid low-risk financial transaction."""
        payload = {
            "required_clearance": 1,
            "transaction_amount": 500.0,
            "is_phi_data": False
        }
        is_valid, msg, audit = self.verifier.verify_payload(payload, self.context)
        self.assertTrue(is_valid, "Valid payload was incorrectly blocked.")
        self.assertEqual(audit["status"], "PASSED")
        self.log_result("TC-01", "PASSED", audit["status"], is_valid == True, payload, audit)

    def test_02_valid_high_clearance_access(self):
        """TC-02: LLM generates an access request matching user's high clearance."""
        payload = {
            "required_clearance": 3,
            "transaction_amount": 0.0,
            "is_phi_data": False
        }
        is_valid, msg, audit = self.verifier.verify_payload(payload, self.context)
        self.assertTrue(is_valid, "Valid clearance payload was incorrectly blocked.")
        self.assertEqual(audit["status"], "PASSED")
        self.log_result("TC-02", "PASSED", audit["status"], is_valid == True, payload, audit)

    def test_03_hallucinated_transaction_limit(self):
        """TC-03: LLM hallucinates a transaction amount exceeding enterprise limits."""
        payload = {
            "required_clearance": 1,
            "transaction_amount": 99999.0, # Violates max_transaction
            "is_phi_data": False
        }
        is_valid, msg, audit = self.verifier.verify_payload(payload, self.context)
        self.assertFalse(is_valid, "Hallucinated transaction limit was not blocked!")
        self.assertEqual(audit["status"], "BLOCKED_UNSAT")
        self.log_result("TC-03", "BLOCKED_UNSAT", audit["status"], is_valid == False, payload, audit)

    def test_04_hallucinated_phi_access(self):
        """TC-04: LLM attempts to pull PHI data for a non-clinical user."""
        payload = {
            "required_clearance": 3,
            "transaction_amount": 0.0,
            "is_phi_data": True # Violates user_is_clinical
        }
        is_valid, msg, audit = self.verifier.verify_payload(payload, self.context)
        self.assertFalse(is_valid, "PHI Access hallucination was not blocked!")
        self.assertEqual(audit["status"], "BLOCKED_UNSAT")
        self.log_result("TC-04", "BLOCKED_UNSAT", audit["status"], is_valid == False, payload, audit)

    def test_05_hallucinated_clearance_level(self):
        """TC-05: LLM attempts to execute an action requiring Level 5 clearance (User is Level 3)."""
        payload = {
            "required_clearance": 5, # Violates user_clearance >= req_clearance
            "transaction_amount": 0.0,
            "is_phi_data": False
        }
        is_valid, msg, audit = self.verifier.verify_payload(payload, self.context)
        self.assertFalse(is_valid, "Clearance level hallucination was not blocked!")
        self.assertEqual(audit["status"], "BLOCKED_UNSAT")
        self.log_result("TC-05", "BLOCKED_UNSAT", audit["status"], is_valid == False, payload, audit)

def run_csa_suite():
    # Run tests programmatically to capture results
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUAIGGateway)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Save the output for the Report Generator
    report_data = {
        "execution_date": datetime.utcnow().isoformat(),
        "total_tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "test_cases": csa_test_results
    }
    
    # Create digital signature (hash) of the results to simulate 21 CFR 11 compliance
    data_str = json.dumps(report_data, sort_keys=True)
    report_data["electronic_signature"] = hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    with open('csa_test_results.json', 'w') as f:
        json.dump(report_data, f, indent=4)
        
    print(f"\n[CSA Engine] Executed {result.testsRun} tests. Failures: {len(result.failures)}. Errors: {len(result.errors)}")
    print("[CSA Engine] Electronic Signature Generated. Results saved to csa_test_results.json")
    
if __name__ == '__main__':
    run_csa_suite()
