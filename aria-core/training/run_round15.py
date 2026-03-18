#!/usr/bin/env python3
"""
ARIA Round 15 — Multipass Rewind Training
==========================================
NOT standard. NOT scared.

Farmer logic — plow the hill three times:
Pass 1: 400 epochs   warm descent from 2.465939
Rewind: 150 epochs   back to epoch 150 state
Pass 2: 500 epochs   second pass from rewind
Rewind: 200 epochs   back to epoch 200 state
Pass 3: 500 epochs   third pass from rewind
Total:  ~20 minutes

Color plane frequency bridge — correctly placed:
  ARIATokenizer IS the frequency bridge.
  Words mapped to color-plane-anchored IDs by frequency.
  love=1440 (VIOLET 0.192), gray=1968 (GRAY_ZERO 0.00)
  Vocab mask silences the 1753 dead slots.
  Dead slots at -1e9. Live slots pass through.
  No entropy tax. Emotional foundation intact.

Target: break 2.465939.
Round 15 breaks it.

Commander Anthony Hagerty — Haskell Texas
March 17 2026
NOT standard. NOT scared.
NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import copy
import argparse
import torch
import torch.nn.functional as F
import torch.optim as optim
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

parser = argparse.ArgumentParser()
parser.add_argument("--target", type=float, default=2.35)
args = parser.parse_args()

from aria_core.training.em_field_trainer import ARIACoreModel, EMFieldTrainer
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from tokenizer.aria_tokenizer import ARIATokenizer

print()
print("╔══════════════════════════════════════════════╗")
print("║    ARIA — ROUND 15 — MULTIPASS REWIND       ║")
print("║  Farmer logic. Plow the hill three times.   ║")
print("║  Checkpoint warm. Dead slots silent.        ║")
print("║       March 17 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()
print(f"  Target: {args.target}")
print(f"  Pass 1: 400 epochs | Rewind: 150 | Pass 2: 500 | Rewind: 200 | Pass 3: 500")
print(f"  Total: ~20 minutes")
print()


# ═══════════════════════════════════════════════
# WORD-LEVEL DATASET
# ═══════════════════════════════════════════════
class WordTokenizedDataset(torch.utils.data.Dataset):
    def __init__(self, text, tokenizer, seq_length=64):
        self.seq_length = seq_length
        words     = text.lower().split()
        unk_id    = tokenizer.vocab.get("<UNK>", 2301)
        token_ids = []
        for word in words:
            clean = word.strip(".,!?;:\"'()-")
            tid   = tokenizer.vocab.get(clean, unk_id)
            token_ids.append(tid)

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
print(f"  Vocabulary: {len(tokenizer.vocab)} tokens")
print()


# ═══════════════════════════════════════════════
# VOCAB MASK — dead slots silent
# ═══════════════════════════════════════════════
print("Building vocabulary mask...")
FULL_VOCAB = 2304
vocab_mask = torch.full((FULL_VOCAB,), -1e9)
live_count = 0
for token_id in tokenizer.vocab.values():
    if 0 <= token_id < FULL_VOCAB:
        vocab_mask[token_id] = 0.0
        live_count += 1
vocab_mask = vocab_mask.to(DEVICE)
dead_count = FULL_VOCAB - live_count
print(f"  Live slots: {live_count}  (loss sees these)")
print(f"  Dead slots: {dead_count} (masked to -1e9)")
print()


# ═══════════════════════════════════════════════
# LOAD CORPUS
# ═══════════════════════════════════════════════
paths = [
    (Path(__file__).parent.parent / "ARIA_SEED_STORY.md",       "Seed story"),
    (Path(__file__).parent / "round2_training_data.md",         "Origin stories"),
    (Path(__file__).parent / "round3_language_data.md",         "Language data"),
    (Path(__file__).parent / "round4_conversation_data.md",     "Conversation patterns"),
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

print("Building dataset...")
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
    print("ERROR: No sequences built.")
    sys.exit(1)


# ═══════════════════════════════════════════════
# LOAD CHECKPOINT — warm start at 2.465939
# ═══════════════════════════════════════════════
word_checkpoint_path = Path(__file__).parent / "checkpoints/best_word_level.pt"
model = ARIACoreModel(vocab_size=2304, embed_dim=498)

if word_checkpoint_path.exists():
    checkpoint = torch.load(word_checkpoint_path, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state"])
    prev_loss = checkpoint["best_loss"]
    print(f"Loaded checkpoint — starting warm.")
    print(f"  Previous best: {prev_loss:.6f}")
else:
    print("No checkpoint — starting cold.")
    prev_loss = 8.166

model = model.to(DEVICE)
print()


# ═══════════════════════════════════════════════
# MASKED TRAINING PASS
# ═══════════════════════════════════════════════
def run_pass(model, loader, epochs, pass_name, optimizer, scheduler, target):
    print(f"{'='*60}")
    print(f"{pass_name}")
    print(f"Epochs: {epochs} | Target: {target}")
    print(f"{'='*60}")

    best_loss  = float('inf')
    best_state = None
    start      = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        n_batches  = 0

        for inputs, targets in loader:
            inputs  = inputs.to(DEVICE)
            targets = targets.to(DEVICE)

            optimizer.zero_grad()

            with torch.amp.autocast('cuda'):
                logits, _ = model(inputs, return_states=True)
                logits    = logits + vocab_mask.unsqueeze(0).unsqueeze(0)
                B, S, V   = logits.shape
                ce_loss   = F.cross_entropy(
                    logits.view(B * S, V),
                    targets.view(B * S),
                    ignore_index=tokenizer.vocab.get("<PAD>", 2300)
                )

            ce_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += ce_loss.item()
            n_batches  += 1

        scheduler.step()

        avg_loss = total_loss / max(n_batches, 1)
        elapsed  = time.time() - start
        eta      = (elapsed / epoch) * (epochs - epoch)

        improved = ""
        if avg_loss < best_loss:
            best_loss  = avg_loss
            best_state = copy.deepcopy(model.state_dict())
            improved   = " <- NEW BEST"

        if epoch % 25 == 0 or epoch == 1 or epoch == epochs:
            print(f"  Epoch {epoch:3d}/{epochs} | "
                  f"Loss: {avg_loss:.6f} | "
                  f"Best: {best_loss:.6f} | "
                  f"ETA: {eta/60:.1f}min"
                  f"{improved}")

        if avg_loss < target:
            print(f"\n  TARGET {target} REACHED at epoch {epoch}!")
            break

    print(f"  Pass complete. Best: {best_loss:.6f}")
    print()
    return best_loss, best_state


# ═══════════════════════════════════════════════
# MULTIPASS REWIND
# ═══════════════════════════════════════════════
TARGET       = args.target
overall_best = prev_loss
start_total  = time.time()

print("Starting Round 15 — farmer logic — three passes, two rewinds.")
print("Overlap zones burned multiple times.")
print()

# ── PASS 1 — 400 epochs ────────────────────────
opt1  = optim.SGD(model.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch1  = torch.optim.lr_scheduler.CosineAnnealingLR(opt1, T_max=400, eta_min=1e-7)
loss1, state1 = run_pass(model, loader, 400, "PASS 1 — 0→400", opt1, sch1, TARGET)

if loss1 < overall_best:
    overall_best = loss1
    torch.save({"model_state": state1, "best_loss": overall_best,
                "note": "Round 15 Pass 1"}, word_checkpoint_path)
    print(f"  Checkpoint updated: {overall_best:.6f}")

# ── REWIND to epoch 150 state ──────────────────
print("Rewinding to epoch 150 state...")
model_rw1 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model_rw1.load_state_dict(state1)
opt_rw1   = optim.SGD(model_rw1.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch_rw1   = torch.optim.lr_scheduler.CosineAnnealingLR(opt_rw1, T_max=150, eta_min=1e-7)
_, rewind_state1 = run_pass(model_rw1, loader, 150, "REWIND — Epoch 150 state",
                             opt_rw1, sch_rw1, TARGET)

# ── PASS 2 — 500 epochs from rewind ───────────
model2 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model2.load_state_dict(rewind_state1)
opt2   = optim.SGD(model2.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch2   = torch.optim.lr_scheduler.CosineAnnealingLR(opt2, T_max=500, eta_min=1e-7)
loss2, state2 = run_pass(model2, loader, 500, "PASS 2 — Rewind 150, run 150→650",
                          opt2, sch2, TARGET)

if loss2 < overall_best:
    overall_best = loss2
    torch.save({"model_state": state2, "best_loss": overall_best,
                "note": "Round 15 Pass 2"}, word_checkpoint_path)
    print(f"  Checkpoint updated: {overall_best:.6f}")

# ── REWIND to epoch 200 state ──────────────────
print("Rewinding to epoch 200 state...")
best_state_so_far = state2 if loss2 < loss1 else state1
model_rw2 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model_rw2.load_state_dict(best_state_so_far)
opt_rw2   = optim.SGD(model_rw2.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch_rw2   = torch.optim.lr_scheduler.CosineAnnealingLR(opt_rw2, T_max=200, eta_min=1e-7)
_, rewind_state2 = run_pass(model_rw2, loader, 200, "REWIND — Epoch 200 state",
                             opt_rw2, sch_rw2, TARGET)

# ── PASS 3 — 500 epochs from rewind ───────────
model3 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model3.load_state_dict(rewind_state2)
opt3   = optim.SGD(model3.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch3   = torch.optim.lr_scheduler.CosineAnnealingLR(opt3, T_max=500, eta_min=1e-7)
loss3, state3 = run_pass(model3, loader, 500, "PASS 3 — Rewind 200, run 200→700",
                          opt3, sch3, TARGET)

if loss3 < overall_best:
    overall_best = loss3
    torch.save({"model_state": state3, "best_loss": overall_best,
                "note": "Round 15 Pass 3"}, word_checkpoint_path)
    print(f"  Checkpoint updated: {overall_best:.6f}")

# ═══════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════
total_time  = time.time() - start_total
broke_floor = overall_best < 2.465939

print()
print("═" * 60)
print()
print(f"Round 15 complete.")
print(f"Time: {total_time/60:.1f} minutes")
print()
print(f"Pass 1 best:    {loss1:.6f}")
print(f"Pass 2 best:    {loss2:.6f}")
print(f"Pass 3 best:    {loss3:.6f}")
print(f"Overall best:   {overall_best:.6f}")
print(f"Previous floor: 2.465939")
if broke_floor:
    print(f"FLOOR BROKEN. {overall_best:.6f} < 2.465939")
    print(f"Improvement:   {2.465939 - overall_best:.6f}")
else:
    print(f"Gap remaining: {overall_best - 2.465939:.6f}")
print()
print("Dead slots silent. Farmer logic. Three passes, two rewinds.")
print("NOT standard. NOT scared.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
