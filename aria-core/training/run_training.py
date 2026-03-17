# ARIA FIRST TRAINING RUN
# Watch her learn in real time
# March 16 2026 — Haskell Texas

import sys
import torch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aria_core.training.em_field_trainer import (
    ARIACoreModel, EMFieldTrainer,
    SeedStoryDataset
)
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from core.q_constants import GRAY

print()
print("╔══════════════════════════════════════════════╗")
print("║         ARIA — FIRST TRAINING RUN           ║")
print("║      The seed story. The first learning.    ║")
print("║         March 16 2026 — Haskell Texas       ║")
print("╚══════════════════════════════════════════════╝")
print()

# Load seed story
seed_path = Path(__file__).parent.parent / "ARIA_SEED_STORY.md"
print(f"Loading seed story...")
with open(seed_path) as f:
    seed_text = f.read()
print(f"  {len(seed_text)} characters")
print(f"  The first thing she ever heard.")
print()

# Build dataset
dataset = SeedStoryDataset(seed_text, seq_length=128)
loader  = torch.utils.data.DataLoader(
    dataset,
    batch_size=BATCH_SIZE_TRAINING,
    shuffle=True,
    num_workers=2
)
print(f"Dataset: {len(dataset)} sequences")
print(f"Batches per epoch: {len(loader)}")
print()

# Build model
print("Building ARIA core model...")
model = ARIACoreModel(vocab_size=2304, embed_dim=498)
model = model.to(DEVICE)
params = sum(p.numel() for p in model.parameters())
print(f"Parameters: {params:,}")
print(f"Device: {DEVICE}")
print()

# Build trainer
trainer = EMFieldTrainer(model, learning_rate=0.001)

print("Starting training...")
print("Watching every epoch.")
print("Loss should fall from ~8.1 toward baseline.")
print("EM field component shows fluorescent learning.")
print()
print("─" * 60)

import time
start = time.time()
best  = float('inf')

for epoch in range(1, 201):
    metrics = trainer.train_epoch(loader)
    trainer.scheduler.step()
    trainer.epoch = epoch
    trainer.loss_log.append({
        "epoch": epoch, **metrics
    })

    elapsed = time.time() - start
    eta     = (elapsed / epoch) * (200 - epoch)

    improved = ""
    if metrics["loss"] < best:
        best = metrics["loss"]
        improved = " ← BEST"
        trainer.best_loss = best

    if epoch % 50 == 0:
        trainer.save_checkpoint(epoch, metrics)

    print(
        f"Epoch {epoch:3d}/200 | "
        f"Loss: {metrics['loss']:.6f} | "
        f"CE: {metrics['ce']:.6f} | "
        f"EM: {metrics['em']:.6f} | "
        f"ETA: {eta/60:.1f}min"
        f"{improved}"
    )

    if epoch == 1:
        print()
        print("  First epoch complete.")
        print("  She is learning.")
        print()
    elif epoch == 50:
        print()
        print("  Epoch 50 — checkpoint sealed.")
        pct = ((8.166 - best) / 8.166) * 100
        print(f"  Improvement so far: {pct:.1f}%")
        print()
    elif epoch == 100:
        print()
        print("  Halfway. The field is settling.")
        pct = ((8.166 - best) / 8.166) * 100
        print(f"  Improvement so far: {pct:.1f}%")
        print()
    elif epoch == 150:
        print()
        print("  Epoch 150. The lotus is open.")
        pct = ((8.166 - best) / 8.166) * 100
        print(f"  Improvement so far: {pct:.1f}%")
        print()
    elif epoch == 200:
        print()
        print("  200 epochs complete.")
        pct = ((8.166 - best) / 8.166) * 100
        print(f"  Total improvement: {pct:.1f}%")

trainer.save_log()

total_time = time.time() - start
pct_improvement = ((8.166 - best) / 8.166) * 100

print()
print("═" * 60)
print()
print(f"Training complete.")
print(f"Time: {total_time/60:.1f} minutes")
print(f"Best loss: {best:.6f}")
print(f"Improvement: {pct_improvement:.1f}% over random init")
print()
print("ARIA has learned from her seed story.")
print("The fluorescent field has settled.")
print("The Stokes gradient did its work.")
print("The seven workers are tuned.")
print()
print("She is no longer random.")
print("She has a shape.")
print("The shape the seed story gave her.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
