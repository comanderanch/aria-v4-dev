#!/usr/bin/env python3
"""
ARIA Round 17 — Surgical Transplant + Extended Multipass Rewind
===============================================================
NOT standard. NOT scared.

Round 16 proved the transplant works:
  7.799 → 3.458 → 2.956 → 2.804 in 1750 epochs
  Still descending at Pass 3 epoch 500 — never plateaued
  Loss was lost because it never beat 2.465939 checkpoint gate
  Round 17 fixes both problems

The bridge:
  token_embedding  → word-level  (547 word vocabulary)
  everything else  → char-level best.pt (emotional depth at 2.465939)

Pass 1: 600 epochs   — shock recovery runway
Rewind: 200 epochs
Pass 2: 800 epochs   — adaptation phase
Rewind: 250 epochs
Pass 3: 1000 epochs  — close the gap and break 2.465939
Total:  ~45 minutes

Every pass state saved — progress never lost again.

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

from aria_core.training.em_field_trainer import ARIACoreModel
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from tokenizer.aria_tokenizer import ARIATokenizer

print()
print("╔══════════════════════════════════════════════╗")
print("║   ARIA — ROUND 17 — EXTENDED TRANSPLANT     ║")
print("║  600 / 800 / 1000 epoch runway.             ║")
print("║  Every pass saved. Progress never lost.     ║")
print("║       March 17 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()
print(f"  Target: {args.target}")
print(f"  Pass 1: 600 | Rewind: 200 | Pass 2: 800 | Rewind: 250 | Pass 3: 1000")
print(f"  Total: ~45 minutes")
print()


# ═══════════════════════════════════════════════
# CHECKPOINT PATHS
# ═══════════════════════════════════════════════
ckpt_dir       = Path(__file__).parent / "checkpoints"
char_path      = ckpt_dir / "best.pt"
word_path      = ckpt_dir / "best_word_level.pt"
transplant_path= ckpt_dir / "best_transplant.pt"
pass1_path     = ckpt_dir / "round17_pass1_best.pt"
pass2_path     = ckpt_dir / "round17_pass2_best.pt"
pass3_path     = ckpt_dir / "round17_pass3_best.pt"


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
# SURGICAL TRANSPLANT
# token_embedding  → word-level chain
# everything else  → char-level best.pt
# ═══════════════════════════════════════════════
print("Surgical transplant...")

if not char_path.exists():
    print(f"  ERROR: char-level checkpoint not found — {char_path}")
    sys.exit(1)
if not word_path.exists():
    print(f"  ERROR: word-level checkpoint not found — {word_path}")
    sys.exit(1)

char_ckpt  = torch.load(char_path, map_location='cpu')
word_ckpt  = torch.load(word_path, map_location='cpu')
char_state = char_ckpt["model_state"]
word_state = word_ckpt["model_state"]

transplant_state = {}
for key in char_state:
    if key == "token_embedding.weight":
        transplant_state[key] = word_state[key].clone()
        print(f"  token_embedding    <- word-level  "
              f"{list(word_state[key].shape)}  (547 word vocabulary)")
    else:
        transplant_state[key] = char_state[key].clone()

char_layers = [k for k in char_state if k != "token_embedding.weight"]
print(f"  {len(char_layers)} layers    <- char-level  "
      f"(emotional foundation at {char_ckpt['best_loss']:.6f})")
print(f"    fluorescent.*    — emotional processing layer")
print(f"    expander.*       — 498D dimensional expansion")
print(f"    worker_heads.*   — 7 knights")
print(f"    kings_chamber.*  — collapse geometry")
print(f"    output_norm.*    — output normalization")

torch.save({
    "model_state": transplant_state,
    "best_loss":   char_ckpt["best_loss"],
    "note":        "Round 17 surgical transplant — char internals + word embedding",
}, transplant_path)
print(f"  Transplant sealed: {transplant_path.name}")
print()

model = ARIACoreModel(vocab_size=2304, embed_dim=498)
model.load_state_dict(transplant_state)
model = model.to(DEVICE)
prev_loss = char_ckpt["best_loss"]

print(f"Model loaded.")
print(f"  Internal layers: char-level depth ({prev_loss:.6f})")
print(f"  Embedding table: word-level vocabulary")
print()


# ═══════════════════════════════════════════════
# MASKED TRAINING PASS
# Saves best state to save_path unconditionally
# ═══════════════════════════════════════════════
def run_pass(model, loader, epochs, pass_name, optimizer, scheduler,
             target, save_path):
    print(f"{'='*60}")
    print(f"{pass_name}")
    print(f"Epochs: {epochs} | Target: {target} | Saving: {save_path.name}")
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

        if epoch % 50 == 0 or epoch == 1 or epoch == epochs:
            print(f"  Epoch {epoch:4d}/{epochs} | "
                  f"Loss: {avg_loss:.6f} | "
                  f"Best: {best_loss:.6f} | "
                  f"ETA: {eta/60:.1f}min"
                  f"{improved}")

        if avg_loss < target:
            print(f"\n  TARGET {target} REACHED at epoch {epoch}!")
            break

    # Always save — floor gate removed
    torch.save({
        "model_state": best_state,
        "best_loss":   best_loss,
        "pass":        pass_name,
        "note":        f"Round 17 — {pass_name}",
    }, save_path)
    print(f"  Saved: {save_path.name}  loss={best_loss:.6f}")
    print(f"  Pass complete. Best: {best_loss:.6f}")
    print()
    return best_loss, best_state


# ═══════════════════════════════════════════════
# MULTIPASS REWIND — extended runway
# ═══════════════════════════════════════════════
TARGET      = args.target
start_total = time.time()
floor       = 2.465939

print("Starting Round 17 — extended transplant training.")
print("600 epochs shock recovery. 800 adaptation. 1000 to close the gap.")
print()

# ── PASS 1 — 600 epochs (shock recovery) ──────
opt1  = optim.SGD(model.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch1  = torch.optim.lr_scheduler.CosineAnnealingLR(opt1, T_max=600, eta_min=1e-7)
loss1, state1 = run_pass(model, loader, 600,
                          "PASS 1 — Shock recovery 0→600",
                          opt1, sch1, TARGET, pass1_path)

# Update word-level checkpoint if new best
if loss1 < floor:
    floor = loss1
    torch.save({"model_state": state1, "best_loss": floor,
                "note": "Round 17 Pass 1 — FLOOR BROKEN"}, word_path)
    print(f"  FLOOR BROKEN — word checkpoint updated: {floor:.6f}")

# ── REWIND to epoch 200 state ──────────────────
print("Rewinding to epoch 200 state...")
model_rw1 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model_rw1.load_state_dict(state1)
opt_rw1   = optim.SGD(model_rw1.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch_rw1   = torch.optim.lr_scheduler.CosineAnnealingLR(opt_rw1, T_max=200, eta_min=1e-7)
rw1_save  = ckpt_dir / "round17_rewind1_best.pt"
_, rewind_state1 = run_pass(model_rw1, loader, 200,
                             "REWIND — Epoch 200 state",
                             opt_rw1, sch_rw1, TARGET, rw1_save)

# ── PASS 2 — 800 epochs (adaptation) ──────────
model2 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model2.load_state_dict(rewind_state1)
opt2   = optim.SGD(model2.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch2   = torch.optim.lr_scheduler.CosineAnnealingLR(opt2, T_max=800, eta_min=1e-7)
loss2, state2 = run_pass(model2, loader, 800,
                          "PASS 2 — Adaptation 200→1000",
                          opt2, sch2, TARGET, pass2_path)

if loss2 < floor:
    floor = loss2
    torch.save({"model_state": state2, "best_loss": floor,
                "note": "Round 17 Pass 2 — FLOOR BROKEN"}, word_path)
    print(f"  FLOOR BROKEN — word checkpoint updated: {floor:.6f}")

# ── REWIND to epoch 250 state ──────────────────
print("Rewinding to epoch 250 state...")
best_state_so_far = state2 if loss2 < loss1 else state1
model_rw2 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model_rw2.load_state_dict(best_state_so_far)
opt_rw2   = optim.SGD(model_rw2.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch_rw2   = torch.optim.lr_scheduler.CosineAnnealingLR(opt_rw2, T_max=250, eta_min=1e-7)
rw2_save  = ckpt_dir / "round17_rewind2_best.pt"
_, rewind_state2 = run_pass(model_rw2, loader, 250,
                             "REWIND — Epoch 250 state",
                             opt_rw2, sch_rw2, TARGET, rw2_save)

# ── PASS 3 — 1000 epochs (close the gap) ──────
model3 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model3.load_state_dict(rewind_state2)
opt3   = optim.SGD(model3.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch3   = torch.optim.lr_scheduler.CosineAnnealingLR(opt3, T_max=1000, eta_min=1e-7)
loss3, state3 = run_pass(model3, loader, 1000,
                          "PASS 3 — Close the gap 250→1250",
                          opt3, sch3, TARGET, pass3_path)

if loss3 < floor:
    floor = loss3
    torch.save({"model_state": state3, "best_loss": floor,
                "note": "Round 17 Pass 3 — FLOOR BROKEN"}, word_path)
    print(f"  FLOOR BROKEN — word checkpoint updated: {floor:.6f}")

# ═══════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════
total_time  = time.time() - start_total
overall_best = min(loss1, loss2, loss3)
broke_floor  = overall_best < 2.465939

print()
print("═" * 60)
print()
print(f"Round 17 complete.")
print(f"Time: {total_time/60:.1f} minutes")
print()
print(f"Transplant base:  2.465939  (char-level emotional foundation)")
print(f"Pass 1 best:      {loss1:.6f}  -> {pass1_path.name}")
print(f"Pass 2 best:      {loss2:.6f}  -> {pass2_path.name}")
print(f"Pass 3 best:      {loss3:.6f}  -> {pass3_path.name}")
print(f"Overall best:     {overall_best:.6f}")
print(f"Previous floor:   2.465939")
if broke_floor:
    print(f"FLOOR BROKEN.     {overall_best:.6f} < 2.465939")
    print(f"Improvement:      {2.465939 - overall_best:.6f}")
    print(f"word checkpoint:  updated — {word_path.name}")
else:
    print(f"Gap remaining:    {overall_best - 2.465939:.6f}")
    print(f"Round 18 starts from pass3_best: {loss3:.6f}")
print()
print("Char-level depth. Word-level vocabulary. Two chains bridged.")
print("Progress saved at every pass. Nothing lost.")
print("NOT standard. NOT scared.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
