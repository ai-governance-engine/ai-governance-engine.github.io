"""
Universal AI Governance - Lightweight Environment Recognizer & Router
Encodes demonstration grid pairs (X_demo, Y_demo) into 9-dimensional softmax distribution.
Total memory footprint < 5 MB. Target classification accuracy >= 95.0%.
"""
import time
import numpy as np
from typing import Tuple, List, Dict, Any
from core.arc_invariant_contracts import ARCGridContract, RouterWeightsContract


class EnvironmentRouter:
    """Extracts spatial invariant features and routes to 9 ARC domains."""
    
    FEATURE_DIM = 9
    NUM_DOMAINS = 9
    
    def __init__(self, seed: int = 1337):
        # Calibrated projection matrix: maps the 9 orthogonal feature channels to domain logits
        # Feature channels:
        # 0: Topology -> Domain 1 (idx 0)
        # 1: Isometry -> Domain 2 (idx 1)
        # 2: Tessellation -> Domain 3 (idx 2)
        # 3: CellularAutomata -> Domain 4 (idx 3)
        # 4: Raycasting -> Domain 5 (idx 4)
        # 5: Palette -> Domain 6 (idx 5)
        # 6: Occlusion -> Domain 7 (idx 6)
        # 7: Parity -> Domain 8 (idx 7)
        # 8: Reversal -> Domain 9 (idx 8)
        self.W = np.zeros((self.FEATURE_DIM, self.NUM_DOMAINS), dtype=np.float32)
        for i in range(9):
            self.W[i, i] = 12.0
            
        self.b = np.zeros(self.NUM_DOMAINS, dtype=np.float32)

    def _check_isometry(self, x: np.ndarray, y: np.ndarray) -> bool:
        transforms = [
            np.rot90(x, k=-1),
            np.rot90(x, k=1),
            np.rot90(x, k=2),
            np.fliplr(x),
            np.flipud(x),
            x.T
        ]
        for t in transforms:
            if t.shape == y.shape and np.array_equal(t, y):
                return True
        return False

    def extract_features(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Extracts 9-dimensional spatial invariant feature vector."""
        feat = np.zeros(self.FEATURE_DIM, dtype=np.float32)
        
        hx, wx = x.shape
        hy, wy = y.shape
        
        # Check Parity (Domain 8, idx 7): 1x1 scalar output
        if hy == 1 and wy == 1 and (hx > 1 or wx > 1):
            feat[7] = 1.0
            return feat
            
        # Check Tessellation (Domain 3, idx 2): integer tile repetition
        if (hy % hx == 0 and wy % wx == 0) and (hy > hx or wy > wx):
            if np.array_equal(y, np.tile(x, (hy // hx, wy // wx))):
                feat[2] = 1.0
                return feat
                
        # Check Reversal / Identity (Domain 9, idx 8)
        if np.array_equal(x, y):
            feat[8] = 1.0
            return feat
            
        # Check Isometry (Domain 2, idx 1)
        if self._check_isometry(x, y):
            feat[1] = 1.0
            return feat
            
        # Check Raycasting (Domain 5, idx 4)
        ray_found = False
        for r in range(hx):
            row_x, row_y = x[r, :], y[r, :]
            if not np.array_equal(row_x, row_y):
                diff_indices = np.where(row_x != row_y)[0]
                if len(diff_indices) > 0:
                    start_c = diff_indices[0]
                    ray_c = row_y[start_c]
                    if ray_c != 0 and np.all(row_y[start_c:] == ray_c):
                        copy_y = y.copy()
                        copy_y[r, start_c:] = x[r, start_c:]
                        if np.array_equal(copy_y, x):
                            ray_found = True
                            break
        if ray_found:
            feat[4] = 1.0
            return feat
            
        # Check Cellular Automata (Domain 4, idx 3): gravity compaction
        grav = True
        for c in range(wx):
            col = x[:, c]
            nz = col[col != 0]
            if len(nz) > 0:
                exp = np.zeros(hx, dtype=np.int32)
                exp[hx - len(nz):] = nz
                if not np.array_equal(y[:, c], exp):
                    grav = False
                    break
        if grav and not np.array_equal(x, y):
            feat[3] = 1.0
            return feat
            
        # Check Occlusion (Domain 7, idx 6): masked zero cells, rest identical
        diff = (x != y)
        if np.any(diff) and np.all(y[diff] == 0) and np.all(x[~diff] == y[~diff]):
            feat[6] = 1.0
            return feat
            
        # Check Palette (Domain 6, idx 5): color substitution
        ux, uy = set(np.unique(x)), set(np.unique(y))
        if ux != uy:
            feat[5] = 1.0
            return feat
            
        # Default fallback: Topology (Domain 1, idx 0)
        feat[0] = 1.0
        return feat

    def route_demonstration(self, g_in: ARCGridContract, g_out: ARCGridContract) -> RouterWeightsContract:
        """
        Routes a single demo grid pair to a 9-dimensional probability vector.
        Guarantees sum(weights) == 1.0 (stochastic simplex).
        """
        x = np.array(g_in.cells, dtype=np.int32)
        y = np.array(g_out.cells, dtype=np.int32)
        
        feats = self.extract_features(x, y)
        logits = (feats @ self.W) + self.b
        
        # Softmax with numerical stability
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        
        probs = probs.astype(np.float64)
        probs /= np.sum(probs)
        weights_tuple = tuple(float(round(p, 6)) for p in probs)
        diff = 1.0 - sum(weights_tuple)
        weights_list = list(weights_tuple)
        weights_list[0] += diff
        
        return RouterWeightsContract(weights=tuple(weights_list))

    def evaluate_batch_accuracy(self, samples: List[Tuple[ARCGridContract, ARCGridContract, int]]) -> float:
        """Computes top-1 domain routing accuracy over test samples."""
        correct = 0
        for g_in, g_out, true_domain in samples:
            weights = self.route_demonstration(g_in, g_out)
            pred_domain = int(np.argmax(weights.weights)) + 1
            if pred_domain == true_domain:
                correct += 1
        return (correct / max(1, len(samples))) * 100.0
