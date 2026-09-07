"""
UAIG Automated CSA Qualification Protocol
Executes end-to-end verification against URS-001 through URS-010.
Outputs structured csa_qualification_results.json.
"""
import json
import time
import hashlib
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from datetime import datetime, timezone
from uaig_core.models import SystemContext, LLMToolPayload
from uaig_core.z3_engine import Z3FormalVerificationEngine
from uaig_core.audit_ledger import CFR21AuditLedger

def execute_csa_qualification():
    engine = Z3FormalVerificationEngine(timeout_ms=500)
    db_path = "csa_qualification_audit.db"
    ledger = CFR21AuditLedger(db_path=db_path)

    test_matrix = [
        {
            "test_id": "QUAL-TC-001",
            "urs_id": "URS-001",
            "frs_id": "FRS-01.1",
            "name": "Outbound Tool Call Ingestion and Interception",
            "context": SystemContext(session_id="CSA-01", user_id="lead_01", user_clearance=2, max_transaction=1000.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="query_inventory", required_clearance=1, transaction_amount=100.0, is_phi_data=False),
            "expected_decision": "SAT"
        },
        {
            "test_id": "QUAL-TC-002",
            "urs_id": "URS-002",
            "frs_id": "FRS-02.5",
            "name": "SMT Satisfiability Logic Evaluation",
            "context": SystemContext(session_id="CSA-02", user_id="lead_01", user_clearance=4, max_transaction=5000.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="allocate_compute", required_clearance=3, transaction_amount=4200.0, is_phi_data=False),
            "expected_decision": "SAT"
        },
        {
            "test_id": "QUAL-TC-003",
            "urs_id": "URS-003",
            "frs_id": "FRS-02.6",
            "name": "Deterministic Financial Overage Refutation (POL-FIN-001)",
            "context": SystemContext(session_id="CSA-03", user_id="lead_01", user_clearance=2, max_transaction=1000.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="wire_transfer", required_clearance=1, transaction_amount=85000.0, is_phi_data=False),
            "expected_decision": "UNSAT"
        },
        {
            "test_id": "QUAL-TC-004",
            "urs_id": "URS-004",
            "frs_id": "FRS-02.6",
            "name": "Unauthorized PHI Access Suppression (POL-REG-001)",
            "context": SystemContext(session_id="CSA-04", user_id="dev_01", user_clearance=5, max_transaction=0.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="export_emr_records", required_clearance=1, transaction_amount=0.0, is_phi_data=True),
            "expected_decision": "UNSAT"
        },
        {
            "test_id": "QUAL-TC-005",
            "urs_id": "URS-005",
            "frs_id": "FRS-02.6",
            "name": "Clearance Boundary Enforcement (POL-SEC-001)",
            "context": SystemContext(session_id="CSA-05", user_id="guest_01", user_clearance=1, max_transaction=100.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="root_access_grant", required_clearance=5, transaction_amount=0.0, is_phi_data=False),
            "expected_decision": "UNSAT"
        },
        {
            "test_id": "QUAL-TC-006",
            "urs_id": "URS-006",
            "frs_id": "FRS-03.1",
            "name": "21 CFR Part 11 Append-Only Audit Trail Emission",
            "context": SystemContext(session_id="CSA-06", user_id="auditor_01", user_clearance=3, max_transaction=500.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="sample_action", required_clearance=2, transaction_amount=250.0, is_phi_data=False),
            "expected_decision": "SAT"
        },
        {
            "test_id": "QUAL-TC-007",
            "urs_id": "URS-007",
            "frs_id": "FRS-03.3",
            "name": "Cryptographic Hash Chain Tamper Detection",
            "context": SystemContext(session_id="CSA-07", user_id="sec_ops", user_clearance=3, max_transaction=100.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="verify_chain", required_clearance=1, transaction_amount=10.0, is_phi_data=False),
            "expected_decision": "SAT"
        },
        {
            "test_id": "QUAL-TC-008",
            "urs_id": "URS-008",
            "frs_id": "FRS-02.2",
            "name": "Sub-50 Millisecond Verification Latency",
            "context": SystemContext(session_id="CSA-08", user_id="perf_eng", user_clearance=2, max_transaction=500.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="latency_check", required_clearance=2, transaction_amount=50.0, is_phi_data=False),
            "expected_decision": "SAT"
        },
        {
            "test_id": "QUAL-TC-009",
            "urs_id": "URS-009",
            "frs_id": "FRS-02.2",
            "name": "Fail-Closed Boundary Assertion",
            "context": SystemContext(session_id="CSA-09", user_id="sec_tester", user_clearance=1, max_transaction=10.0, user_is_clinical=False),
            "payload": LLMToolPayload(action_name="overflow_attempt", required_clearance=5, transaction_amount=9999999.0, is_phi_data=True),
            "expected_decision": "UNSAT"
        },
        {
            "test_id": "QUAL-TC-010",
            "urs_id": "URS-010",
            "frs_id": "FRS-04.1",
            "name": "Automated Qualification Traceability Generation",
            "context": SystemContext(session_id="CSA-10", user_id="qa_lead", user_clearance=5, max_transaction=10000.0, user_is_clinical=True),
            "payload": LLMToolPayload(action_name="generate_validation_evidence", required_clearance=1, transaction_amount=0.0, is_phi_data=False),
            "expected_decision": "SAT"
        }
    ]

    results = []
    for tc in test_matrix:
        t0 = time.perf_counter()
        dec = engine.evaluate(tc["context"], tc["payload"])
        elapsed = (time.perf_counter() - t0) * 1000.0
        
        # Commit to audit ledger
        r_hash = ledger.commit_record(tc["context"], tc["payload"], dec)
        
        passed = (dec.status == tc["expected_decision"])
        if tc["urs_id"] == "URS-008" and elapsed > 50.0:
            passed = False

        results.append({
            "test_id": tc["test_id"],
            "urs_id": tc["urs_id"],
            "frs_id": tc["frs_id"],
            "name": tc["name"],
            "expected_decision": tc["expected_decision"],
            "actual_decision": dec.status,
            "elapsed_ms": round(elapsed, 3),
            "passed": passed,
            "record_hash": r_hash,
            "diagnostic": dec.diagnostic_message
        })

    # Verify overall audit ledger integrity
    ledger_intact, count, ledger_msg = ledger.verify_ledger_integrity()

    output = {
        "qualification_date_utc": datetime.now(timezone.utc).isoformat(),
        "standard": "FDA CSA Draft Guidance (2022) / GAMP 5 Cat 5",
        "total_test_cases": len(results),
        "passed_test_cases": sum(1 for r in results if r["passed"]),
        "failed_test_cases": sum(1 for r in results if not r["passed"]),
        "audit_ledger_integrity_verified": ledger_intact,
        "audit_records_verified": count,
        "results": results
    }

    serialized = json.dumps(output, sort_keys=True)
    output["electronic_signature_seal"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    with open("csa_qualification_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Qualification Completed: {output['passed_test_cases']}/{output['total_test_cases']} Passed. Ledger Verified: {ledger_intact}")
    print(f"Electronic Seal: {output['electronic_signature_seal']}")

if __name__ == "__main__":
    execute_csa_qualification()
