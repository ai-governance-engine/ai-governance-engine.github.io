import os
import pytest
import numpy as np
from student.multi_lora_manager import MultiLoRAManager

def test_load_trained_loras():
    weights_path = os.path.join("dist", "weights", "domain_loras_trained.npz")
    assert os.path.exists(weights_path), f"File {weights_path} not found"
    
    manager = MultiLoRAManager(in_features=2048, out_features=2048, rank=16, alpha=32.0)
    manager.load_from_npz(weights_path)
    
    for d in range(1, 10):
        adapter = manager.adapters[d]
        assert adapter.A.shape == (16, 2048)
        assert adapter.B.shape == (2048, 16)
        assert not np.isnan(adapter.A).any()
        assert not np.isnan(adapter.B).any()
        assert not np.all(adapter.A == 0.0)
        assert not np.all(adapter.B == 0.0)

def test_trained_lora_forward_latency_and_finite():
    weights_path = os.path.join("dist", "weights", "domain_loras_trained.npz")
    manager = MultiLoRAManager(in_features=2048, out_features=2048, rank=16, alpha=32.0)
    manager.load_from_npz(weights_path)
    
    rng = np.random.default_rng(42)
    base_w = rng.normal(0.0, 0.02, size=(2048, 2048)).astype(np.float32)
    x = rng.normal(0.0, 1.0, size=(2048,)).astype(np.float32)
    
    # Test each domain active
    for d in range(1, 10):
        weights = [0.0] * 9
        weights[d - 1] = 1.0
        elapsed_ms = manager.set_routing_weights(tuple(weights))
        assert elapsed_ms < 0.1, f"Routing latency {elapsed_ms}ms exceeded 0.1ms"
        
        y = manager.forward(x, base_w)
        assert y.shape == (2048,)
        assert np.isfinite(y).all()
        assert not np.isnan(y).any()
