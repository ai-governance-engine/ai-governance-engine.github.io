"""
Universal AI Governance - ARC-AGI-3 Edge Inference Runtime
Integrates 3D Tensorized Student Base Model, Multi-LoRA Manager, and Environment Router.
"""
import time
import numpy as np
from typing import Dict, Any, Optional, Tuple
from core.arc_invariant_contracts import ARCGridContract, RouterWeightsContract
from student.multi_lora_manager import MultiLoRAManager
from student.environment_router import EnvironmentRouter
from core.tensor_train_factorizer import TensorTrainFactorizer


class ARC3InferenceRuntime:
    """Unified ultra-fast edge runtime for ARC-AGI-3 task solving."""
    
    def __init__(self, hidden_dim: int = 1024, rank: int = 16):
        self.hidden_dim = hidden_dim
        self.router = EnvironmentRouter()
        self.lora_manager = MultiLoRAManager(
            in_features=hidden_dim,
            out_features=hidden_dim,
            rank=rank
        )
        # Initialize 3D Tensorized Base Model weights
        rng = np.random.default_rng(42)
        base_w = rng.normal(0.0, 0.02, size=(hidden_dim, hidden_dim)).astype(np.float32)
        self.factorizer = TensorTrainFactorizer(rank=rank)
        # Factorize base matrix into 3D tensor cores
        self.U_in, self.G_core, self.U_out, self.metrics = self.factorizer.factorize_matrix_to_3d_core(
            base_w, mode_k=8
        )
        # Reconstruct base slice (mode k=0)
        self.reconstructed_base = self.U_in @ self.G_core[:, :, 0] @ self.U_out

    def execute_inference_step(
        self,
        demo_in: ARCGridContract,
        demo_out: ARCGridContract,
        test_in: ARCGridContract
    ) -> Tuple[np.ndarray, RouterWeightsContract, float]:
        """
        Executes end-to-end forward inference:
        1. Router extracts demonstration features and outputs routing vector alpha in Delta^8
        2. LoRA manager updates weights in < 0.1ms
        3. 3D tensorized student executes forward prediction
        """
        t0 = time.perf_counter()
        # 1. Environment routing
        routing_weights = self.router.route_demonstration(demo_in, demo_out)
        
        # 2. Dynamic LoRA Composition
        self.lora_manager.set_routing_weights(routing_weights.weights)
        
        # 3. Model forward pass on embedded grid
        x_in = np.zeros(self.hidden_dim, dtype=np.float32)
        flat_cells = [c for row in test_in.cells for c in row]
        x_in[:min(len(flat_cells), self.hidden_dim)] = flat_cells[:self.hidden_dim]
        
        pred_latent = self.lora_manager.forward(x_in, self.reconstructed_base)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        
        return pred_latent, routing_weights, elapsed_ms
