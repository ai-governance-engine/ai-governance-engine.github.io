"""
Unit tests for TT-SVD factorizer and 3D tensor contraction kernel.
"""
import numpy as np
from core.tensor_train_factorizer import TensorTrainFactorizer
from core.tensor_contraction_kernel import TensorContractionKernel


def test_tt_factorizer_metrics():
    factorizer = TensorTrainFactorizer(rank=32)
    rng = np.random.default_rng(42)
    # Realistic low-rank weight matrix (rank <= 32)
    W = (rng.normal(0.0, 1.0, size=(512, 32)) @ rng.normal(0.0, 1.0, size=(32, 512))).astype(np.float32)
    
    U_in, G_core, U_out, metrics = factorizer.factorize_matrix_to_3d_core(W, mode_k=8)
    
    assert metrics["energy_preserved_pct"] >= 99.0, f"Energy {metrics['energy_preserved_pct']}% < 99%"
    assert metrics["compression_ratio"] >= 4.0, f"Compression ratio {metrics['compression_ratio']} < 4.0"
    assert metrics["reconstruction_error"] <= 0.05, f"Recon error {metrics['reconstruction_error']} > 0.05"


def test_contraction_kernel_latency():
    import time
    kernel = TensorContractionKernel()
    x = np.random.randn(1, 512).astype(np.float32)
    U_in = np.random.randn(512, 32).astype(np.float32)
    G = np.random.randn(32, 32, 8).astype(np.float32)
    U_out = np.random.randn(32, 512).astype(np.float32)
    z = np.random.randn(8).astype(np.float32)
    
    t0 = time.perf_counter()
    y = kernel.contract(x, U_in, G, U_out, z_steering=z)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    
    assert y.shape == (1, 512)
    assert elapsed_ms < 1.0, f"Contraction took {elapsed_ms}ms (criterion < 1.0ms)"
