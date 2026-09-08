"""
Unit tests for all 9 Z3 SMT domain verification oracles.
"""
import numpy as np
from core.arc_invariant_contracts import ARCGridContract
from core.z3_arc_oracles import MasterARCOracle


def make_grid(arr: np.ndarray) -> ARCGridContract:
    return ARCGridContract(
        height=arr.shape[0],
        width=arr.shape[1],
        cells=tuple(tuple(int(x) for x in row) for row in arr)
    )


def test_all_9_oracles_sat():
    master = MasterARCOracle()
    
    # 1. Topology
    g1_in = make_grid(np.array([[1, 2], [0, 1]]))
    g1_out = make_grid(np.array([[1, 1], [0, 2]]))
    c1 = master.verify_step(1, g1_in, g1_out, {})
    assert c1.is_valid and c1.status == "SAT"
    assert c1.elapsed_ms < 15.0
    
    # 2. Isometry
    arr_2 = np.array([[1, 2], [3, 4]])
    g2_in = make_grid(arr_2)
    g2_out = make_grid(np.rot90(arr_2, k=-1))
    c2 = master.verify_step(2, g2_in, g2_out, {"isometry_type": "rot90"})
    assert c2.is_valid and c2.status == "SAT"
    assert c2.elapsed_ms < 15.0
    
    # 3. Tessellation
    arr_3 = np.array([[1, 2], [3, 4]])
    g3_in = make_grid(arr_3)
    g3_out = make_grid(np.tile(arr_3, (2, 2)))
    c3 = master.verify_step(3, g3_in, g3_out, {})
    assert c3.is_valid and c3.status == "SAT"
    assert c3.elapsed_ms < 15.0
    
    # 4. Cellular Automata
    g4_in = make_grid(np.array([[1, 0], [0, 2]]))
    g4_out = make_grid(np.array([[0, 0], [1, 2]]))
    c4 = master.verify_step(4, g4_in, g4_out, {"direction": "down"})
    assert c4.is_valid and c4.status == "SAT"
    assert c4.elapsed_ms < 15.0
    
    # 5. Raycasting
    g5_in = make_grid(np.array([[2, 0, 0], [0, 0, 0]]))
    g5_out = make_grid(np.array([[2, 2, 2], [0, 0, 0]]))
    c5 = master.verify_step(5, g5_in, g5_out, {"ray_color": 2})
    assert c5.is_valid and c5.status == "SAT"
    assert c5.elapsed_ms < 15.0
    
    # 6. Palette
    g6_in = make_grid(np.array([[1, 2], [2, 1]]))
    g6_out = make_grid(np.array([[3, 4], [4, 3]]))
    c6 = master.verify_step(6, g6_in, g6_out, {"color_map": {"1": 3, "2": 4}})
    assert c6.is_valid and c6.status == "SAT"
    assert c6.elapsed_ms < 15.0
    
    # 7. Occlusion
    g7_in = make_grid(np.array([[1, 2], [3, 4]]))
    g7_out = make_grid(np.array([[1, 0], [3, 4]]))
    c7 = master.verify_step(7, g7_in, g7_out, {"mask_color": 0})
    assert c7.is_valid and c7.status == "SAT"
    assert c7.elapsed_ms < 15.0
    
    # 8. Parity
    g8_in = make_grid(np.array([[1, 1], [1, 1]]))
    g8_out = make_grid(np.array([[1]]))
    c8 = master.verify_step(8, g8_in, g8_out, {"modulus": 2})
    assert c8.is_valid and c8.status == "SAT"
    assert c8.elapsed_ms < 15.0
    
    # 9. Reversal
    arr_9 = np.array([[1, 2], [3, 4]])
    g9_in = make_grid(arr_9)
    g9_out = make_grid(arr_9)
    c9 = master.verify_step(9, g9_in, g9_out, {})
    assert c9.is_valid and c9.status == "SAT"
    assert c9.elapsed_ms < 15.0


def test_oracles_unsat_counterexamples():
    master = MasterARCOracle()
    
    # Vocabulary leak in Domain 1
    g1_in = make_grid(np.array([[1, 2], [0, 1]]))
    g1_bad = make_grid(np.array([[9, 8], [7, 6]]))
    c1 = master.verify_step(1, g1_in, g1_bad, {})
    assert not c1.is_valid and c1.status == "UNSAT"
    assert c1.counterexample is not None
