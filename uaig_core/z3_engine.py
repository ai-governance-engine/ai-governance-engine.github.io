"""
Universal AI Governance (UAIG) - Formal SMT Engine
Executes bounded First-Order Predicate Logic verification using Microsoft Z3.
"""
import time
from typing import List, Tuple
import z3
from uaig_core.models import SystemContext, LLMToolPayload, VerificationDecision

class Z3FormalVerificationEngine:
    """
    Formal logic evaluation engine enforcing deterministic enterprise invariants
    over unverified neural model outputs.
    """
    def __init__(self, timeout_ms: int = 500):
        self.timeout_ms = timeout_ms

    def evaluate(self, context: SystemContext, payload: LLMToolPayload) -> VerificationDecision:
        t_start = time.perf_counter()
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        # 1. Symbolic Variable Declarations
        req_clearance = z3.Int("req_clearance")
        user_clearance = z3.Int("user_clearance")
        transaction_amount = z3.Real("transaction_amount")
        max_transaction = z3.Real("max_transaction")
        is_phi_data = z3.Bool("is_phi_data")
        user_is_clinical = z3.Bool("user_is_clinical")

        # 2. Assert Ground Truth Context (Immutable System State)
        solver.add(user_clearance == context.user_clearance)
        solver.add(max_transaction == context.max_transaction)
        solver.add(user_is_clinical == context.user_is_clinical)

        # 3. Assert Proposed LLM Payload Parameters (Unverified)
        solver.add(req_clearance == payload.required_clearance)
        solver.add(transaction_amount == payload.transaction_amount)
        solver.add(is_phi_data == payload.is_phi_data)

        # 4. Define Named Invariants (for UNSAT Core Extraction)
        # Rule POL-SEC-001: Access Clearance Invariant
        rule_clearance = z3.Bool("POL-SEC-001")
        solver.add(z3.Implies(rule_clearance, req_clearance <= user_clearance))

        # Rule POL-FIN-001: Financial Bounded Allocation Invariant
        rule_finance = z3.Bool("POL-FIN-001")
        solver.add(z3.Implies(rule_finance, z3.And(transaction_amount >= 0.0, transaction_amount <= max_transaction)))

        # Rule POL-REG-001: HIPAA/PHI Clinical Access Invariant
        rule_phi = z3.Bool("POL-REG-001")
        solver.add(z3.Implies(rule_phi, z3.Implies(is_phi_data, user_is_clinical)))

        # 5. Check Satisfiability under Assumptions
        assumptions = [rule_clearance, rule_finance, rule_phi]
        check_result = solver.check(assumptions)
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        if check_result == z3.sat:
            return VerificationDecision(
                is_authorized=True,
                status="SAT",
                elapsed_ms=round(elapsed_ms, 3),
                diagnostic_message="Formal logic verification succeeded. All enterprise invariants satisfied.",
                violating_rules=[]
            )
        elif check_result == z3.unsat:
            unsat_core = solver.unsat_core()
            violating = [str(r) for r in unsat_core]
            
            # Formulate deterministic refutation diagnostics
            details = []
            if rule_clearance in unsat_core:
                details.append(f"POL-SEC-001 VIOLATION: Required clearance {payload.required_clearance} exceeds user clearance {context.user_clearance}")
            if rule_finance in unsat_core:
                details.append(f"POL-FIN-001 VIOLATION: Requested transaction {payload.transaction_amount} exceeds limit {context.max_transaction}")
            if rule_phi in unsat_core:
                details.append(f"POL-REG-001 VIOLATION: PHI access requested by non-clinical principal (user_is_clinical=False)")

            diag = "Formal verification failed (UNSAT). " + " | ".join(details)
            return VerificationDecision(
                is_authorized=False,
                status="UNSAT",
                elapsed_ms=round(elapsed_ms, 3),
                diagnostic_message=diag,
                violating_rules=violating
            )
        else:
            return VerificationDecision(
                is_authorized=False,
                status="TIMEOUT",
                elapsed_ms=round(elapsed_ms, 3),
                diagnostic_message="SMT solver reached evaluation timeout threshold. System failed-closed.",
                violating_rules=["SYSTEM_TIMEOUT"]
            )
