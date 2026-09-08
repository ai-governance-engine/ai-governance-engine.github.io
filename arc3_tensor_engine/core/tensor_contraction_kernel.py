"""
3D Tensor Contraction Kernel with Latent Mode-K Gating
Implements fused tensor contractions over the 3-mode core tensor.
"""
import numpy as np
from typing import Optional

class TensorContractionKernel:
    def __init__(self, systolic_dim: int = 128):
        self.systolic_dim = systolic_dim

    def contract(
        self,
        x: np.ndarray,
        u_in: np.ndarray,
        g_core: np.ndarray,
        u_out: np.ndarray,
        z_steering: Optional[np.ndarray] = None
    ) -> np.ndarray:
        B, D_in = x.shape
        R, _, mode_k = g_core.shape

        if z_steering is None:
            # Default to base manifold k=0
            z = np.zeros((mode_k,), dtype=x.dtype)
            z[0] = 1.0
        else:
            z = z_steering

        # 1. Project input into rank space: h_r = x @ U_in
        h_r = np.dot(x, u_in) # [B, R]

        # 2. Contract Core along Mode-K using steering vector: G_steered = sum_k z[k] * G[:, :, k]
        g_steered = np.tensordot(g_core, z, axes=([2], [0])) # [R, R]

        # 3. Internal latent contraction: h_mid = h_r @ G_steered
        h_mid = np.dot(h_r, g_steered) # [B, R]

        # 4. Project out to target space: y = h_mid @ U_out
        y = np.dot(h_mid, u_out) # [B, D_out]

        return y
