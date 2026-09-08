"""
Unit tests for fail-closed rejection sampling gate.
"""
import numpy as np
from core.arc_invariant_contracts import ARCGridContract, ARCTransformationStep
from core.fail_closed_rejection_gate import FailClosedRejectionGate


def make_grid(arr: np.ndarray) -> ARCGridContract:
    return ARCGridContract(
        height=arr.shape[0],
        width=arr.shape[1],
        cells=tuple(tuple(int(x) for x in row) for row in arr)
    )


def test_fail_closed_gate_behavior():
    gate = FailClosedRejectionGate()
    
    # Valid step
    arr = np.array([[1, 2], [3, 4]])
    step_valid = ARCTransformationStep(
        step_id=1,
        domain_id=2,
        operation_name="rotate_90",
        parameters={"isometry_type": "rot90"},
        state_before=make_grid(arr),
        state_after=make_grid(np.rot90(arr, k=-1))
    )
    res_sat = gate.evaluate_and_filter(step_valid)
    assert res_sat.is_committed is True
    assert res_sat.status == "COMMITTED_SAT"
    assert res_sat.certified_trace is not None
    assert len(res_sat.proof_certificate.proof_digest) == 64
    
    # Invalid step
    step_invalid = ARCTransformationStep(
        step_id=2,
        domain_id=2,
        operation_name="corrupted",
        parameters={"isometry_type": "rot90"},
        state_before=make_grid(arr),
        state_after=make_grid(np.zeros_like(arr))
    )
    res_unsat = gate.evaluate_and_filter(step_invalid)
    assert res_unsat.is_committed is False
    assert res_unsat.status == "REJECTED_UNSAT"
    assert res_unsat.certified_trace is None
