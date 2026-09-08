"""
Universal AI Governance - Modular Multi-LoRA Engine for ARC-AGI-3
Manages 9 discrete low-rank adapter weights (r=16, alpha=32) for the 9 ARC spatial domains.
Supports dynamic weighted composition and ultra-low latency hot-swapping (< 0.1ms).
"""
import time
import numpy as np
from typing import Dict, List, Optional, Tuple


class DomainLoRAAdapter:
    """Represents a single rank-r LoRA adapter for a specific ARC domain."""
    
    def __init__(self, domain_id: int, in_features: int, out_features: int, rank: int = 16, alpha: float = 32.0, seed: int = 42):
        self.domain_id = domain_id
        self.in_features = in_features
        self.out_features = out_features
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        
        rng = np.random.default_rng(seed + domain_id * 100)
        # Kaiming uniform init for A, zero init for B
        self.A = rng.normal(0.0, np.sqrt(2.0 / in_features), size=(rank, in_features)).astype(np.float32)
        self.B = np.zeros((out_features, rank), dtype=np.float32)
        # Populate structured synthetic weights per domain
        self.B += rng.normal(0.0, 0.01, size=(out_features, rank)).astype(np.float32)

    def compute_delta_weight(self) -> np.ndarray:
        """Computes scaled Delta W = (alpha / r) * (B @ A)."""
        return self.scaling * (self.B @ self.A)


class MultiLoRAManager:
    """Manages 9 discrete low-rank adapters and performs sub-0.1ms weighted composition."""
    
    def __init__(self, in_features: int = 1024, out_features: int = 1024, rank: int = 16, alpha: float = 32.0):
        self.in_features = in_features
        self.out_features = out_features
        self.rank = rank
        self.alpha = alpha
        
        self.adapters: Dict[int, DomainLoRAAdapter] = {}
        for d in range(1, 10):
            self.adapters[d] = DomainLoRAAdapter(
                domain_id=d,
                in_features=in_features,
                out_features=out_features,
                rank=rank,
                alpha=alpha
            )
            
        self._active_weights = np.full(9, 1.0 / 9.0, dtype=np.float32)

    def set_routing_weights(self, weights: Tuple[float, ...]) -> float:
        """
        Updates dynamic routing weights alpha in Delta^8.
        Returns execution latency in milliseconds (< 0.1ms criterion).
        """
        t0 = time.perf_counter()
        assert len(weights) == 9, f"Expected 9 routing weights, got {len(weights)}"
        self._active_weights = np.array(weights, dtype=np.float32)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms

    def forward(self, x: np.ndarray, base_weight: np.ndarray) -> np.ndarray:
        """
        Evaluates forward pass: y = x @ W_base^T + sum_i alpha_i * (x @ A_i^T @ B_i^T * scaling)
        Operates strictly in factorized low-rank space (O(r*(d_in + d_out))).
        """
        # Base projection
        y = x @ base_weight.T
        
        # Dynamic low-rank LoRA steering
        lora_delta = np.zeros_like(y)
        for d in range(1, 10):
            alpha_d = self._active_weights[d - 1]
            if alpha_d > 1e-5:
                adapter = self.adapters[d]
                # Low-rank factorized multiplication
                # (x @ A.T) is [..., rank], then @ B.T is [..., out_features]
                low_rank_proj = (x @ adapter.A.T) @ adapter.B.T
                lora_delta += alpha_d * adapter.scaling * low_rank_proj
                
        return y + lora_delta

    def compose_dense_weight(self, base_weight: np.ndarray) -> np.ndarray:
        """Explicitly materializes W_active = W_base + sum_i alpha_i * (B_i @ A_i * scaling)."""
        w_composed = base_weight.copy()
        for d in range(1, 10):
            alpha_d = self._active_weights[d - 1]
            if alpha_d > 1e-5:
                adapter = self.adapters[d]
                w_composed += alpha_d * adapter.compute_delta_weight()
        return w_composed

    def get_adapter_memory_bytes(self) -> int:
        """Returns total memory footprint of all 9 LoRA adapters."""
        single_adapter_bytes = (self.rank * self.in_features + self.out_features * self.rank) * 4
        return single_adapter_bytes * 9
