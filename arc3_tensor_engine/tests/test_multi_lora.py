"""
Unit tests for MultiLoRAManager: low-rank projection, reweighting latency, memory footprint.
"""
import numpy as np
from student.multi_lora_manager import MultiLoRAManager


def test_multi_lora_manager():
    mgr = MultiLoRAManager(in_features=512, out_features=512, rank=16)
    
    # 1. Check memory footprint
    mem_mb = mgr.get_adapter_memory_bytes() / (1024 * 1024)
    assert mem_mb < 50.0, f"Memory {mem_mb}MB exceeds 50MB"
    
    # 2. Check reweighting latency (< 0.1ms criterion)
    weights = tuple([1.0 / 9.0] * 9)
    lat_ms = mgr.set_routing_weights(weights)
    assert lat_ms < 0.1, f"Reweighting took {lat_ms}ms (> 0.1ms)"
    
    # 3. Forward pass execution
    x = np.random.randn(512).astype(np.float32)
    w_base = np.random.randn(512, 512).astype(np.float32) * 0.02
    y = mgr.forward(x, w_base)
    assert y.shape == (512,)
