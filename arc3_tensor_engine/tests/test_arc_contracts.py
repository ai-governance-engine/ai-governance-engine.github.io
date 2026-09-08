"""
Unit tests for Pydantic V2 strictly typed contracts and invariant validation.
"""
import pytest
from pydantic import ValidationError
from core.arc_invariant_contracts import ARCGridContract, ARCTransformationStep, RouterWeightsContract


def test_valid_grid():
    grid = ARCGridContract(
        height=3,
        width=3,
        cells=((0, 1, 2), (3, 4, 5), (6, 7, 8))
    )
    assert grid.height == 3
    assert grid.width == 3
    assert len(grid.cells) == 3


def test_invalid_color_code():
    with pytest.raises(ValidationError):
        ARCGridContract(
            height=2,
            width=2,
            cells=((0, 10), (0, 0)) # 10 is illegal (> 9)
        )


def test_invalid_dimension_mismatch():
    with pytest.raises(ValidationError):
        ARCGridContract(
            height=2,
            width=3,
            cells=((0, 1), (0, 0)) # row length 2 != width 3
        )


def test_router_weights_stochastic_invariant():
    # Valid stochastic vector
    w = RouterWeightsContract(weights=tuple([1.0 / 9.0] * 9))
    assert len(w.weights) == 9
    
    # Non-stochastic vector (sum != 1.0)
    with pytest.raises(ValidationError):
        RouterWeightsContract(weights=(0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5))
