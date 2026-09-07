"""
Universal AI Governance (UAIG) - FastAPI Proxy Gateway
Exposes production REST endpoints for LLM tool-call interception,
formal logic verification, and 21 CFR Part 11 audit inspection.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from uaig_core.models import (
    InterceptRequest, InterceptResponse, VerificationDecision, AuditRecordSchema
)
from uaig_core.z3_engine import Z3FormalVerificationEngine
from uaig_core.audit_ledger import CFR21AuditLedger

app = FastAPI(
    title="Universal AI Governance (UAIG) Gateway",
    version="1.0.0",
    description="Neuro-Symbolic Enterprise Proxy enforcing SMT formal verification on LLM outputs.",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = Z3FormalVerificationEngine(timeout_ms=500)
ledger = CFR21AuditLedger(db_path="uaig_audit_ledger.db")

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "HEALTHY", "engine": "Microsoft Z3 SMT", "compliance": "FDA 21 CFR Part 11 / CSA"}

@app.post("/v1/intercept", response_model=InterceptResponse)
def intercept_payload(request: InterceptRequest):
    # 1. Execute formal verification under Z3
    decision = engine.evaluate(request.context, request.payload)

    # 2. Commit audit trail record with cryptographic chaining
    record_hash = ledger.commit_record(request.context, request.payload, decision)

    # 3. Augment decision with verified record hash
    final_decision = VerificationDecision(
        is_authorized=decision.is_authorized,
        status=decision.status,
        elapsed_ms=decision.elapsed_ms,
        diagnostic_message=decision.diagnostic_message,
        violating_rules=decision.violating_rules,
        record_hash=record_hash
    )

    return InterceptResponse(
        authorized=final_decision.is_authorized,
        decision=final_decision
    )

@app.get("/v1/audit/records", response_model=list[AuditRecordSchema])
def get_audit_records(limit: int = 50):
    return ledger.list_records(limit=limit)

@app.get("/v1/audit/verify")
def verify_audit_ledger():
    is_valid, count, message = ledger.verify_ledger_integrity()
    return {
        "integrity_verified": is_valid,
        "records_evaluated": count,
        "message": message
    }
