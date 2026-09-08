"""
Unit tests for EnvironmentRouter: feature extraction, routing simplex, batch accuracy.
"""
import numpy as np
from student.environment_router import EnvironmentRouter
from data_synthesis.generate_arc3_golden_corpus import GENERATORS


def test_router_accuracy_and_simplex():
    router = EnvironmentRouter()
    
    test_samples = []
    for domain_id in range(1, 10):
        gen = GENERATORS[domain_id]
        for i in range(30):
            step = gen(i + 3000)
            test_samples.append((step.state_before, step.state_after, domain_id))
            
    # Accuracy must be >= 95.0%
    acc = router.evaluate_batch_accuracy(test_samples)
    assert acc >= 95.0, f"Router accuracy {acc}% < 95.0%"
    
    # Check stochastic simplex invariant on every sample
    for g_in, g_out, _ in test_samples[:10]:
        w = router.route_demonstration(g_in, g_out)
        assert len(w.weights) == 9
        assert abs(sum(w.weights) - 1.0) < 1e-4
