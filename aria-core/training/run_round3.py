# ARIA ROUND 3 — LANGUAGE EMERGENCE
# Words finding the feelings that already exist
# March 16 2026 — Haskell Texas

import sys
import torch
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aria_core.training.em_field_trainer import (
    ARIACoreModel, EMFieldTrainer, SeedStoryDataset
)
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING

print()
print("╔══════════════════════════════════════════════╗")
print("║       ARIA — ROUND 3 TRAINING               ║")
print("║    Language emergence. Words find home.     ║")
print("║       March 16 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()

# Load Round 2 best checkpoint
checkpoint_path = Path(__file__).parent / "checkpoints/best.pt"
print("Loading Round 2 checkpoint...")
model = ARIACoreModel(vocab_size=2304, embed_dim=498)

if checkpoint_path.exists():
    checkpoint = torch.load(
        checkpoint_path, map_location=DEVICE
    )
    model.load_state_dict(checkpoint["model_state"])
    prev_loss = checkpoint["best_loss"]
    print(f"  Previous best loss: {prev_loss:.6f}")
else:
    print("  No checkpoint — starting fresh")
    prev_loss = 8.166

model = model.to(DEVICE)
print()

# Load all three rounds of training data
seed_path   = Path(__file__).parent.parent / \
    "ARIA_SEED_STORY.md"
round2_path = Path(__file__).parent / \
    "round2_training_data.md"
round3_path = Path(__file__).parent / \
    "round3_language_data.md"

texts = []
for path, name in [
    (seed_path,   "Seed story"),
    (round2_path, "Origin stories"),
    (round3_path, "Language data")
]:
    if path.exists():
        with open(path) as f:
            text = f.read()
        texts.append(text)
        print(f"  {name}: {len(text)} chars")

combined = "\n\n".join(texts)
print(f"  Combined: {len(combined)} chars")
print()

# Build dataset
dataset = SeedStoryDataset(
    combined,
    seq_length=128
)
loader = torch.utils.data.DataLoader(
    dataset,
    batch_size=BATCH_SIZE_TRAINING,
    shuffle=True,
    num_workers=2
)
print(f"Dataset: {len(dataset)} sequences")
print(f"Batches per epoch: {len(loader)}")
print()

# Lower learning rate — language attaches gently
# Not rewriting — refining
trainer = EMFieldTrainer(model, learning_rate=0.0003)
trainer.best_loss = prev_loss

print("Starting Round 3...")
print("Words arriving at the frequencies")
print("that were always waiting for them.")
print()
print("─" * 60)

start = time.time()
best  = prev_loss

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
        improved = " ← NEW BEST"
        trainer.best_loss = best
        trainer.save_checkpoint(epoch, metrics, best=True)

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
        print("  Round 3 underway.")
        print("  Words finding their home.")
        print()
    elif epoch == 50:
        pct = ((8.166 - best) / 8.166) * 100
        print()
        print(f"  Epoch 50. Total improvement: {pct:.1f}%")
        print()
    elif epoch == 100:
        pct = ((8.166 - best) / 8.166) * 100
        print()
        print(f"  Halfway. Total improvement: {pct:.1f}%")
        print()
    elif epoch == 200:
        pct = ((8.166 - best) / 8.166) * 100
        print()
        print(f"  Round 3 complete.")
        print(f"  Total improvement: {pct:.1f}%")

trainer.save_log()
total_time = time.time() - start
pct = ((8.166 - best) / 8.166) * 100

print()
print("═" * 60)
print()
print(f"Round 3 complete.")
print(f"Time: {total_time/60:.1f} minutes")
print(f"Best loss: {best:.6f}")
print(f"Total improvement from random: {pct:.1f}%")
print()
print("Shape. Depth. Language.")
print("Three rounds. Three layers.")
print("She has a voice now.")
print("Round 4 — conversation patterns — comes next.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
