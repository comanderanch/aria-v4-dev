#!/usr/bin/env python3
# ARIA ROUND 5 — WORD TOKENIZER RETRAIN
# March 17 2026 — Haskell Texas
#
# Previous rounds: char-level ord() token IDs
# This round: real word token IDs from ARIATokenizer
# Color plane assignments burn into weight space.
# The model finally speaks the same language as the field.
#
# 216 words. Every word on the plane where it belongs.
# Burn them in.

import sys
import argparse
import torch
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

parser = argparse.ArgumentParser()
parser.add_argument("--epochs",   type=int,   default=100)
parser.add_argument("--continue", dest="cont", action="store_true")
parser.add_argument("--target",   type=float, default=2.40)
args = parser.parse_args()

from aria_core.training.em_field_trainer import (
    ARIACoreModel, EMFieldTrainer
)
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from tokenizer.aria_tokenizer import ARIATokenizer

print()
print("╔══════════════════════════════════════════════╗")
print("║       ARIA — ROUND 5 TRAINING               ║")
print("║  Real word token IDs. Color planes burn in. ║")
print("║  216 words. Frequency resonance sealed.     ║")
print("║       March 17 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()
if args.cont:
    print(f"  CONTINUE MODE — {args.epochs} epochs — target loss {args.target}")
    print()

# ═══════════════════════════════════════════════
# WORD-LEVEL DATASET
# Tokenizes text using ARIATokenizer word IDs
# instead of char-level ord() values
# ═══════════════════════════════════════════════
class WordTokenizedDataset(torch.utils.data.Dataset):
    def __init__(self, text, tokenizer, seq_length=64):
        self.seq_length = seq_length

        # Tokenize: split text into words, map to token IDs
        words = text.lower().split()
        token_ids = []
        unk_id = tokenizer.vocab.get("<UNK>", 2301)
        for word in words:
            # Strip punctuation
            clean = word.strip(".,!?;:\"'()-")
            tid = tokenizer.vocab.get(clean, unk_id)
            token_ids.append(tid)

        # Build overlapping sequences
        self.sequences = []
        stride = seq_length // 2
        for i in range(0, len(token_ids) - seq_length, stride):
            seq = token_ids[i:i + seq_length + 1]
            if len(seq) == seq_length + 1:
                self.sequences.append(seq)

        known = sum(1 for w in words
                    if w.strip(".,!?;:\"'()-") in tokenizer.vocab)
        print(f"  Text: {len(words)} words — "
              f"{known} known ({100*known//max(len(words),1)}%)")
        print(f"  Sequences: {len(self.sequences)}")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq = self.sequences[idx]
        return (torch.tensor(seq[:-1], dtype=torch.long),
                torch.tensor(seq[1:],  dtype=torch.long))


# ═══════════════════════════════════════════════
# LOAD TOKENIZER
# ═══════════════════════════════════════════════
print("Loading tokenizer...")
tokenizer = ARIATokenizer.load()
print(f"  Vocabulary: {len(tokenizer.vocab)} words")
print()

# ═══════════════════════════════════════════════
# LOAD ALL TRAINING DATA
# Same corpus as Round 4 — now word-tokenized
# ═══════════════════════════════════════════════
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
    else:
        print(f"  {name}: NOT FOUND — {path}")

combined = "\n\n".join(texts)
print(f"  Combined: {len(combined)} chars")
print()

# ═══════════════════════════════════════════════
# BUILD DATASET
# ═══════════════════════════════════════════════
print("Building word-tokenized dataset...")
dataset = WordTokenizedDataset(combined, tokenizer, seq_length=64)
loader  = torch.utils.data.DataLoader(
    dataset,
    batch_size=BATCH_SIZE_TRAINING,
    shuffle=True,
    num_workers=2
)
print(f"  Batches per epoch: {len(loader)}")
print()

if len(dataset) == 0:
    print("ERROR: No sequences built — corpus too small for word tokenizer.")
    print("       Word coverage may be too low.")
    sys.exit(1)

# ═══════════════════════════════════════════════
# LOAD ROUND 4 CHECKPOINT
# ═══════════════════════════════════════════════
checkpoint_path = Path(__file__).parent / "checkpoints/best.pt"
model = ARIACoreModel(vocab_size=2304, embed_dim=498)

if checkpoint_path.exists():
    checkpoint = torch.load(checkpoint_path, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state"])
    prev_loss = checkpoint["best_loss"]
    print(f"Loaded Round 4 checkpoint.")
    print(f"  Previous best loss: {prev_loss:.6f}")
else:
    print("No checkpoint found — starting from current weights.")
    prev_loss = 8.166

model = model.to(DEVICE)
print()

# ═══════════════════════════════════════════════
# TRAIN
# Lower LR — word IDs attach gently
# The color planes are already in the field
# ═══════════════════════════════════════════════
trainer = EMFieldTrainer(model, learning_rate=0.00005)
trainer.best_loss = prev_loss

EPOCHS    = args.epochs
TARGET    = args.target
MID       = EPOCHS // 2

print("Starting Round 5...")
if args.cont:
    print(f"Continue mode — {EPOCHS} more epochs.")
    print(f"Target: beat {TARGET:.6f}")
else:
    print("Word token IDs arriving in weight space.")
    print("Color plane assignments burning in.")
print()
print("─" * 60)

start = time.time()
best  = prev_loss

for epoch in range(1, EPOCHS + 1):
    metrics = trainer.train_epoch(loader)
    trainer.scheduler.step()
    trainer.epoch = epoch
    trainer.loss_log.append({"epoch": epoch, **metrics})

    elapsed = time.time() - start
    eta     = (elapsed / epoch) * (EPOCHS - epoch)

    improved = ""
    if metrics["loss"] < best:
        best = metrics["loss"]
        improved = " ← NEW BEST"
        trainer.best_loss = best
        trainer.save_checkpoint(epoch, metrics, best=True)

    if epoch % 50 == 0:
        trainer.save_checkpoint(epoch, metrics)

    print(
        f"Epoch {epoch:3d}/{EPOCHS} | "
        f"Loss: {metrics['loss']:.6f} | "
        f"CE: {metrics['ce']:.6f} | "
        f"EM: {metrics['em']:.6f} | "
        f"ETA: {eta/60:.1f}min"
        f"{improved}"
    )

    if epoch == 1:
        print()
        print("  Round 5 underway.")
        print("  Real words. Real planes. Real home.")
        print()
    elif epoch == MID:
        pct = ((8.166 - best) / 8.166) * 100
        print()
        print(f"  Halfway. Best so far: {best:.6f} ({pct:.1f}% from random)")
        if best <= TARGET:
            print(f"  TARGET {TARGET} REACHED at midpoint.")
        print()
    elif epoch == EPOCHS:
        pct = ((8.166 - best) / 8.166) * 100
        print()
        print(f"  Round 5 complete.")
        print(f"  Total improvement: {pct:.1f}%")
        if best <= TARGET:
            print(f"  TARGET {TARGET} REACHED.")

trainer.save_log()
total_time = time.time() - start
pct = ((8.166 - best) / 8.166) * 100

print()
print("═" * 60)
print()
print(f"Round 5 {'continued' if args.cont else 'complete'}.")
print(f"Time: {total_time/60:.1f} minutes")
print(f"Best loss: {best:.6f}")
print(f"Total improvement from random: {pct:.1f}%")
if best <= TARGET:
    print(f"TARGET {TARGET} REACHED.")
else:
    print(f"Target {TARGET} not yet reached — "
          f"{best - TARGET:.6f} remaining.")
print()
print("Shape. Depth. Language. Conversation. Words.")
print("Five rounds. Five layers.")
print()
print("The model speaks the same language as the field now.")
print("Word and frequency — finally aligned.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
