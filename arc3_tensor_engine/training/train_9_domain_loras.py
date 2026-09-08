"""
Universal AI Governance - SMT-Grounded Multi-LoRA Fine-Tuning Pipeline for ARC-AGI-3
Trains 9 discrete domain adapters (r=16, alpha=32) using PyTorch on CUDA.
Partitions 10,000 SMT-verified traces from golden_arc3_reasoning_traces.jsonl
and minimizes MSE reconstruction loss against SMT ground-truth targets.
"""
import os
import sys
import json
import time
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.tensor_train_factorizer import TensorTrainFactorizer

DOMAIN_NAMES = {
    1: "Topology",
    2: "Isometry",
    3: "Tessellation",
    4: "CellularAutomata",
    5: "Raycasting",
    6: "Palette",
    7: "Occlusion",
    8: "Parity",
    9: "Reversal"
}


class DomainLoRAModule(nn.Module):
    """PyTorch implementation of Domain LoRA Adapter for gradient backpropagation."""
    
    def __init__(self, in_features: int, out_features: int, rank: int = 16, alpha: float = 32.0):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        
        # Kaiming uniform init for A, zero init for B
        self.A = nn.Parameter(torch.empty(rank, in_features))
        self.B = nn.Parameter(torch.zeros(out_features, rank))
        nn.init.kaiming_uniform_(self.A, a=np.sqrt(5))
        # Add small normal perturbation to B for symmetry breaking
        nn.init.normal_(self.B, mean=0.0, std=0.001)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, in_features)
        # Low-rank factorized steering: (x @ A.T) @ B.T * scaling
        h = torch.matmul(x, self.A.t())  # (batch, rank)
        delta_y = torch.matmul(h, self.B.t()) * self.scaling  # (batch, out_features)
        return delta_y


def embed_grid(grid_dict: dict, hidden_dim: int) -> np.ndarray:
    """
    Vectorizes an ARC grid into a continuous latent representation.
    Encodes spatial cell values, dimensions, and color distributions.
    """
    vec = np.zeros(hidden_dim, dtype=np.float32)
    h = int(grid_dict.get("height", 0))
    w = int(grid_dict.get("width", 0))
    cells = grid_dict.get("cells", [])
    flat = [float(c) for row in cells for c in row]
    
    n_cells = min(len(flat), hidden_dim - 16)
    if n_cells > 0:
        # Normalized cell colors in [0, 1]
        vec[:n_cells] = np.array(flat[:n_cells], dtype=np.float32) / 9.0
        
    # Spatial metadata encoded in tail positions
    vec[-1] = float(h) / 30.0
    vec[-2] = float(w) / 30.0
    vec[-3] = float(len(set(flat))) / 10.0 if flat else 0.0
    vec[-4] = float(np.mean(flat)) / 9.0 if flat else 0.0
    vec[-5] = float(np.std(flat)) / 9.0 if flat else 0.0
    return vec


def load_dataset_by_domain(jsonl_path: str, hidden_dim: int):
    """Loads and partitions 10,000 golden SMT traces into 9 domain buckets."""
    domain_inputs = {d: [] for d in range(1, 10)}
    domain_targets = {d: [] for d in range(1, 10)}
    
    print(f"[DATASET] Reading SMT golden traces from {jsonl_path}...")
    t0 = time.perf_counter()
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            d_id = int(record["domain_id"])
            if d_id not in domain_inputs:
                continue
            
            x = embed_grid(record["state_before"], hidden_dim)
            y = embed_grid(record["state_after"], hidden_dim)
            domain_inputs[d_id].append(x)
            domain_targets[d_id].append(y)
            
    elapsed = time.perf_counter() - t0
    total_samples = sum(len(v) for v in domain_inputs.values())
    print(f"[DATASET] Loaded {total_samples} traces across 9 domains in {elapsed:.2f}s.")
    for d in range(1, 10):
        print(f"  Domain {d} ({DOMAIN_NAMES[d]}): {len(domain_inputs[d])} traces")
        
    return domain_inputs, domain_targets


def train_domain_loras(
    jsonl_path: str,
    output_weights_path: str,
    hidden_dim: int = 2048,
    rank: int = 16,
    alpha: float = 32.0,
    epochs: int = 80,
    lr: float = 0.01,
    batch_size: int = 64
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 88)
    print(f"  MULTI-LoRA FINE-TUNING PIPELINE: 9 ARC-AGI-3 DOMAINS")
    print(f"  Target Device: {device} | Dim: {hidden_dim} | Rank: {rank} | Alpha: {alpha}")
    print("=" * 88)
    
    # 1. Synthesize 3D Tensorized Base Model Projection
    rng = np.random.default_rng(42)
    base_w_np = rng.normal(0.0, 0.02, size=(hidden_dim, hidden_dim)).astype(np.float32)
    factorizer = TensorTrainFactorizer(rank=64)
    U_in, G_core, U_out, _ = factorizer.factorize_matrix_to_3d_core(base_w_np, mode_k=8)
    reconstructed_base_np = U_in @ G_core[:, :, 0] @ U_out
    base_weight_t = torch.tensor(reconstructed_base_np, dtype=torch.float32, device=device)
    
    # 2. Load dataset
    domain_inputs, domain_targets = load_dataset_by_domain(jsonl_path, hidden_dim)
    
    trained_weights = {}
    training_metrics = {}
    
    t_start_all = time.perf_counter()
    
    for d in range(1, 10):
        d_name = DOMAIN_NAMES[d]
        x_np = np.array(domain_inputs[d], dtype=np.float32)
        y_np = np.array(domain_targets[d], dtype=np.float32)
        
        # Convert to tensors
        x_t = torch.tensor(x_np, dtype=torch.float32, device=device)
        y_t = torch.tensor(y_np, dtype=torch.float32, device=device)
        
        # Calculate base model projection and residual target: R = Y - X @ W_base.T
        with torch.no_grad():
            base_pred = torch.matmul(x_t, base_weight_t.t())
            residual_target = y_t - base_pred
            
        dataset = TensorDataset(x_t, residual_target)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Instantiate Domain LoRA
        model = DomainLoRAModule(in_features=hidden_dim, out_features=hidden_dim, rank=rank, alpha=alpha).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-4)
        criterion = nn.MSELoss()
        
        # Measure initial loss
        with torch.no_grad():
            init_pred = model(x_t)
            init_loss = criterion(init_pred, residual_target).item()
            
        t0_dom = time.perf_counter()
        for epoch in range(1, epochs + 1):
            model.train()
            for bx, by in loader:
                optimizer.zero_grad()
                pred = model(bx)
                loss = criterion(pred, by)
                loss.backward()
                optimizer.step()
            scheduler.step()
            
        t_dom = time.perf_counter() - t0_dom
        
        # Measure final loss
        model.eval()
        with torch.no_grad():
            final_pred = model(x_t)
            final_loss = criterion(final_pred, residual_target).item()
            
        loss_reduction = (1.0 - (final_loss / max(1e-8, init_loss))) * 100.0
        
        print(f"  [Domain {d}: {d_name:<18}] Init MSE: {init_loss:.6f} -> Final MSE: {final_loss:.6f} "
              f"| Delta: {loss_reduction:6.2f}% | Time: {t_dom:5.2f}s")
              
        # Store numpy weights
        trained_weights[f"A_{d}"] = model.A.detach().cpu().numpy().astype(np.float32)
        trained_weights[f"B_{d}"] = model.B.detach().cpu().numpy().astype(np.float32)
        training_metrics[f"domain_{d}"] = {
            "name": d_name,
            "init_loss": float(init_loss),
            "final_loss": float(final_loss),
            "loss_reduction_pct": float(loss_reduction),
            "train_time_sec": float(t_dom),
            "samples": int(len(x_np))
        }
        
    total_time = time.perf_counter() - t_start_all
    print("=" * 88)
    print(f"[COMPLETE] All 9 Domain LoRAs fine-tuned in {total_time:.2f} seconds.")
    
    # 3. Save to npz
    os.makedirs(os.path.dirname(os.path.abspath(output_weights_path)), exist_ok=True)
    np.savez_compressed(
        output_weights_path,
        hidden_dim=hidden_dim,
        rank=rank,
        alpha=alpha,
        **trained_weights
    )
    print(f"[SAVE] Exported trained weights to {output_weights_path}")
    
    # Save training metrics JSON
    metrics_path = os.path.splitext(output_weights_path)[0] + "_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(training_metrics, f, indent=2)
    print(f"[SAVE] Exported training metrics to {metrics_path}")
    
    return training_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train 9 Domain LoRAs on SMT-verified dataset.")
    parser.add_argument("--jsonl", type=str, default="data_synthesis/golden_arc3_reasoning_traces.jsonl", help="Path to golden JSONL dataset")
    parser.add_argument("--output", type=str, default="dist/weights/domain_loras_trained.npz", help="Output path for trained weights")
    parser.add_argument("--dim", type=int, default=2048, help="Hidden dimension size")
    parser.add_argument("--rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--alpha", type=float, default=32.0, help="LoRA alpha")
    parser.add_argument("--epochs", type=int, default=80, help="Training epochs per domain")
    parser.add_argument("--lr", type=float, default=0.01, help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=64, help="Batch size")
    args = parser.parse_args()
    
    train_domain_loras(
        jsonl_path=args.jsonl,
        output_weights_path=args.output,
        hidden_dim=args.dim,
        rank=args.rank,
        alpha=args.alpha,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size
    )
