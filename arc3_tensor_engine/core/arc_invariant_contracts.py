"""
Universal AI Governance - ARC-AGI-3 Strictly Typed Contracts
Pydantic V2 schemas for discrete grids, transformations, and SMT proofs.
"""
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ARCGridContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    height: int = Field(..., ge=1, le=30, description="Grid row count (1-30)")
    width: int = Field(..., ge=1, le=30, description="Grid column count (1-30)")
    cells: Tuple[Tuple[int, ...], ...] = Field(..., description="Immutable 2D grid matrix")

    @field_validator("cells")
    @classmethod
    def validate_cells(cls, cells, info):
        h = len(cells)
        if h < 1 or h > 30:
            raise ValueError(f"Invalid row count: {h}")
        w = len(cells[0])
        if w < 1 or w > 30:
            raise ValueError(f"Invalid column count: {w}")
        if info.data:
            expected_h = info.data.get("height")
            if expected_h is not None and h != expected_h:
                raise ValueError(f"Row count {h} does not match declared height {expected_h}")
            expected_w = info.data.get("width")
            if expected_w is not None and w != expected_w:
                raise ValueError(f"Column count {w} does not match declared width {expected_w}")
        for r_idx, row in enumerate(cells):
            if len(row) != w:
                raise ValueError(f"Row {r_idx} length {len(row)} does not match width {w}")
            for c_idx, val in enumerate(row):
                if val < 0 or val > 9:
                    raise ValueError(f"Invalid color code {val} at ({r_idx}, {c_idx}). Must be in [0, 9].")
        return cells

class ARCTransformationStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: int = Field(..., ge=0)
    domain_id: int = Field(..., ge=1, le=9, description="Target domain [1-9]")
    operation_name: str = Field(...)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    state_before: ARCGridContract
    state_after: ARCGridContract

class SMTProofCertificate(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain_id: int = Field(..., ge=1, le=9)
    status: str = Field(..., description="'SAT' or 'UNSAT'")
    is_valid: bool
    proof_digest: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash")
    invariants_verified: List[str]
    elapsed_ms: float
    counterexample: Optional[str] = None

class RouterWeightsContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    weights: Tuple[float, ...] = Field(..., min_length=9, max_length=9)

    @field_validator("weights")
    @classmethod
    def validate_stochastic(cls, weights):
        total = sum(weights)
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Router weights must sum to 1.0, got {total}")
        for w in weights:
            if w < 0.0 or w > 1.0:
                raise ValueError(f"Weight {w} out of probability range [0, 1]")
        return weights
