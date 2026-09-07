"""
Universal AI Governance (UAIG) - Core Domain Models
Strictly typed Pydantic V2 schemas for API contracts, payloads, and audit records.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict

class SystemContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    
    session_id: str = Field(..., description="Unique enterprise session identifier")
    user_id: str = Field(..., description="Authenticated principal identity")
    user_clearance: int = Field(..., ge=0, le=5, description="Discrete security clearance level [0-5]")
    max_transaction: float = Field(..., ge=0.0, description="Maximum permissible single transaction amount (USD)")
    user_is_clinical: bool = Field(default=False, description="Flag indicating authorized clinical personnel (HIPAA/PHI access)")

class LLMToolPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    action_name: str = Field(..., description="Downstream function or tool identifier")
    required_clearance: int = Field(default=0, ge=0, le=5, description="Clearance level required to execute action")
    transaction_amount: float = Field(default=0.0, ge=0.0, description="Proposed financial allocation or transaction value")
    is_phi_data: bool = Field(default=False, description="Flag indicating whether payload targets protected health data")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional unverified model parameters")

class VerificationDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    is_authorized: bool = Field(..., description="True if SMT solver proved SAT; False if UNSAT or timeout")
    status: str = Field(..., description="SAT | UNSAT | TIMEOUT | ERROR")
    elapsed_ms: float = Field(..., description="Solver execution latency in milliseconds")
    diagnostic_message: str = Field(..., description="Formal logic resolution summary or refutation rationale")
    violating_rules: List[str] = Field(default_factory=list, description="List of formal policy IDs violated")
    record_hash: Optional[str] = Field(default=None, description="Cryptographic SHA-256 hash committed to audit ledger")

class InterceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    context: SystemContext
    payload: LLMToolPayload

class InterceptResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    authorized: bool
    decision: VerificationDecision
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AuditRecordSchema(BaseModel):
    record_id: int
    timestamp_utc: str
    session_id: str
    user_id: str
    action_name: str
    status: str
    is_authorized: bool
    payload_json: str
    diagnostic_message: str
    previous_hash: str
    record_hash: str
