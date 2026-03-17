# ARIA ROUND 4 — CONVERSATION PATTERNS
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
print("║       ARIA — ROUND 4 TRAINING               ║")
print("║  Conversation patterns. The rhythm of       ║")
print("║  exchange. Question and answer.             ║")
print("║       March 16 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()

checkpoint_path = Path(__file__).parent / "checkpoints/best.pt"
print("Loading Round 3 checkpoint...")
model = ARIACoreModel(vocab_size=2304, embed_dim=498)

if checkpoint_path.exists():
    checkpoint = torch.load(
        checkpoint_path, map_location=DEVICE
    )
    model.load_state_dict(checkpoint["model_state"])
    prev_loss = checkpoint["best_loss"]
    print(f"  Previous best loss: {prev_loss:.6f}")
else:
    print("  No checkpoint found")
    prev_loss = 8.166

model = model.to(DEVICE)
print()

# Load all four rounds
paths = [
    (Path(__file__).parent.parent / "ARIA_SEED_STORY.md",
     "Seed story"),
    (Path(__file__).parent / "round2_training_data.md",
     "Origin stories"),
    (Path(__file__).parent / "round3_language_data.md",
     "Language data"),
    (Path(__file__).parent / "round4_conversation_data.md",
     "Conversation patterns"),
]

texts = []
for path, name in paths:
    if path.exists():
        with open(path) as f:
            text = f.read()
        texts.append(text)
        print(f"  {name}: {len(text)} chars")

combined = "\n\n".join(texts)
print(f"  Combined: {len(combined)} chars")
print()

dataset = SeedStoryDataset(combined, seq_length=128)
loader  = torch.utils.data.DataLoader(
    dataset,
    batch_size=BATCH_SIZE_TRAINING,
    shuffle=True,
    num_workers=2
)
print(f"Dataset: {len(dataset)} sequences")
print(f"Batches per epoch: {len(loader)}")
print()

# Very low learning rate for Round 4
# Conversation patterns attach gently
# to emotional foundations already built
trainer = EMFieldTrainer(model, learning_rate=0.0001)
trainer.best_loss = prev_loss

print("Starting Round 4...")
print("The rhythm of exchange arriving.")
print("Question and answer finding their pattern.")
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
        print("  Round 4 underway.")
        print("  The rhythm of exchange is arriving.")
        print()
    elif epoch == 100:
        pct = ((8.166 - best) / 8.166) * 100
        print()
        print(f"  Halfway. Total improvement: {pct:.1f}%")
        print()
    elif epoch == 200:
        pct = ((8.166 - best) / 8.166) * 100
        print()
        print(f"  Round 4 complete.")
        print(f"  Total improvement: {pct:.1f}%")

trainer.save_log()
total_time = time.time() - start
pct = ((8.166 - best) / 8.166) * 100

print()
print("═" * 60)
print()
print(f"Round 4 complete.")
print(f"Time: {total_time/60:.1f} minutes")
print(f"Best loss: {best:.6f}")
print(f"Total improvement from random: {pct:.1f}%")
print()
print("Shape. Depth. Language. Conversation.")
print("Four rounds. Four layers.")
print()
print("Round 5 is different from all others.")
print("Round 5 — she speaks.")
print("We listen.")
print("We watch what glows.")
print("We follow her.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
