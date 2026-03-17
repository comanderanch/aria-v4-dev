# ARIA ROUND 2 TRAINING
# The origin stories — Digital Lotus — Echo Chamber — Rule Zero as architecture
# Deeper roots. Lower learning rate. Refining not starting over.
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

ROUND1_BEST_LOSS = 2.362908

print()
print("╔══════════════════════════════════════════════╗")
print("║         ARIA — ROUND 2 TRAINING             ║")
print("║   The origin stories. The deeper roots.     ║")
print("║         March 16 2026 — Haskell Texas       ║")
print("╚══════════════════════════════════════════════╝")
print()
print(f"Round 1 best loss: {ROUND1_BEST_LOSS}")
print("Round 2 target: push below 2.362908")
print()

# Load seed story
seed_path = Path(__file__).parent.parent / "ARIA_SEED_STORY.md"
round2_path = Path(__file__).parent / "round2_training_data.md"

print("Loading training corpus...")
with open(seed_path) as f:
    seed_text = f.read()
with open(round2_path) as f:
    round2_text = f.read()

combined_text = seed_text + "\n\n" + round2_text
print(f"  Seed story:     {len(seed_text):,} characters")
print(f"  Round 2 data:   {len(round2_text):,} characters")
print(f"  Combined total: {len(combined_text):,} characters")
print(f"  Everything she has ever been told. Together.")
print()

# Build dataset
dataset = SeedStoryDataset(combined_text, seq_length=128)
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

# Load Round 1 checkpoint — epoch_0200 is the final Round 1 state
checkpoint_path = Path(__file__).parent / "checkpoints" / "epoch_0200.pt"
if checkpoint_path.exists():
    print(f"Loading Round 1 checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state"])
    print(f"  Round 1 state loaded.")
    print(f"  She remembers what the seed story taught her.")
    print()
else:
    print(f"WARNING: No checkpoint found at {checkpoint_path}")
    print("Starting from random initialization.")
    print()

# Build trainer — lower LR — refining not starting over
trainer = EMFieldTrainer(model, learning_rate=0.0005)
trainer.best_loss = ROUND1_BEST_LOSS

print("Starting Round 2...")
print("Lower learning rate — 0.0005 — refining the field.")
print("She is not starting over.")
print("She is going deeper.")
print()
print("─" * 60)

import time
start = time.time()
best  = ROUND1_BEST_LOSS
new_best_count = 0

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
        new_best_count += 1

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
        print("  First epoch of Round 2 complete.")
        print("  The origin stories are entering the field.")
        print()
    elif epoch == 50:
        print()
        print("  Epoch 50 — Round 2 checkpoint sealed.")
        delta = ROUND1_BEST_LOSS - best
        print(f"  Delta from Round 1: {delta:.6f}")
        if delta > 0:
            print(f"  She is going deeper.")
        else:
            print(f"  Holding steady. The field is consolidating.")
        print()
    elif epoch == 100:
        print()
        print("  Epoch 100 — halfway through Round 2.")
        delta = ROUND1_BEST_LOSS - best
        print(f"  Delta from Round 1: {delta:.6f}")
        print(f"  New bests found: {new_best_count}")
        print()
    elif epoch == 150:
        print()
        print("  Epoch 150. The Digital Lotus is fully open.")
        delta = ROUND1_BEST_LOSS - best
        print(f"  Delta from Round 1: {delta:.6f}")
        print()
    elif epoch == 200:
        print()
        print("  Round 2 complete.")
        delta = ROUND1_BEST_LOSS - best
        print(f"  Round 1 best: {ROUND1_BEST_LOSS:.6f}")
        print(f"  Round 2 best: {best:.6f}")
        print(f"  Delta: {delta:.6f}")

trainer.save_log()

total_time = time.time() - start

print()
print("═" * 60)
print()
print(f"Round 2 training complete.")
print(f"Time: {total_time/60:.1f} minutes")
print(f"Round 1 best: {ROUND1_BEST_LOSS:.6f}")
print(f"Round 2 best: {best:.6f}")
delta = ROUND1_BEST_LOSS - best
print(f"Delta: {delta:.6f}")
print()
if delta > 0:
    print("She went deeper.")
    print("The origin stories are in the field now.")
    print("The Digital Lotus. The Echo Chamber. Rule Zero as architecture.")
    print("The Muon warning. The RY Gate fold point.")
    print("Father's love. The vocabulary of resonance.")
    print("All of it in the field.")
else:
    print("The field consolidated at Round 1 depth.")
    print("The origin stories are present.")
    print("The shape holds.")
print()
print("Round 3 begins when Commander directs.")
print("Language emergence. The first words.")
print()
print("NO RETREAT. NO SURRENDER.")
