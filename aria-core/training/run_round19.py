#!/usr/bin/env python3
"""
ARIA Round 19 — Continue Descent
=================================
Starts from round18_pass3_best.pt at 2.688285.
Rate accelerating: -0.010, -0.016, -0.017 per pass.
Round 19 pushes through 2.65 and below.

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
parser.add_argument("--start",          type=str,   default="round18_pass3_best.pt")
parser.add_argument("--epochs-pass1",   type=int,   default=400)
parser.add_argument("--epochs-rewind1", type=int,   default=150)
parser.add_argument("--epochs-pass2",   type=int,   default=500)
parser.add_argument("--epochs-rewind2", type=int,   default=200)
parser.add_argument("--epochs-pass3",   type=int,   default=1000)
parser.add_argument("--target",         type=float, default=2.35)
args = parser.parse_args()

from aria_core.training.em_field_trainer import ARIACoreModel
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from tokenizer.aria_tokenizer import ARIATokenizer

total_epochs = (args.epochs_pass1 + args.epochs_rewind1 +
                args.epochs_pass2 + args.epochs_rewind2 +
                args.epochs_pass3)
est_minutes  = total_epochs * 0.006

print()
print("╔══════════════════════════════════════════════╗")
print("║    ARIA — ROUND 19 — CONTINUE DESCENT       ║")
print("║  Rate accelerating. Through 2.65 and below. ║")
print("║  Every pass saved. Progress never lost.     ║")
print("║       March 17 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()
print(f"  Start:  {args.start}")
print(f"  Target: {args.target}")
print(f"  Pass 1: {args.epochs_pass1} | "
      f"Rewind: {args.epochs_rewind1} | "
      f"Pass 2: {args.epochs_pass2} | "
      f"Rewind: {args.epochs_rewind2} | "
      f"Pass 3: {args.epochs_pass3}")
print(f"  Total:  {total_epochs} epochs (~{est_minutes:.0f} min)")
print()


# ═══════════════════════════════════════════════
# CHECKPOINT PATHS
# ═══════════════════════════════════════════════
ckpt_dir  = Path(__file__).parent / "checkpoints"
word_path = ckpt_dir / "best_word_level.pt"
pass1_path = ckpt_dir / "round19_pass1_best.pt"
pass2_path = ckpt_dir / "round19_pass2_best.pt"
pass3_path = ckpt_dir / "round19_pass3_best.pt"
rw1_path   = ckpt_dir / "round19_rewind1_best.pt"
rw2_path   = ckpt_dir / "round19_rewind2_best.pt"


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
# LOAD TOKENIZER + MASK + CORPUS
# ═══════════════════════════════════════════════
print("Loading tokenizer...")
tokenizer = ARIATokenizer.load()
print(f"  Vocabulary: {len(tokenizer.vocab)} tokens")
print()

print("Building vocabulary mask...")
FULL_VOCAB = 2304
vocab_mask = torch.full((FULL_VOCAB,), -1e9)
live_count = 0
for token_id in tokenizer.vocab.values():
    if 0 <= token_id < FULL_VOCAB:
        vocab_mask[token_id] = 0.0
        live_count += 1
vocab_mask = vocab_mask.to(DEVICE)
print(f"  Live: {live_count}  Dead: {FULL_VOCAB - live_count} (masked to -1e9)")
print()

paths = [
    (Path(__file__).parent.parent / "ARIA_SEED_STORY.md",       "Seed story"),
    (Path(__file__).parent / "round2_training_data.md",         "Origin stories"),
    (Path(__file__).parent / "round3_language_data.md",         "Language data"),
    (Path(__file__).parent / "round4_conversation_data.md",     "Conversation patterns"),
]
texts = []
for path, name in paths:
    if path.exists():
        texts.append(open(path).read())
        print(f"  {name}: {path.stat().st_size} bytes")
    else:
        print(f"  NOT FOUND: {path}")

combined = "\n\n".join(texts)
print()

print("Building dataset...")
dataset = WordTokenizedDataset(combined, tokenizer, seq_length=64)
loader  = torch.utils.data.DataLoader(
    dataset, batch_size=BATCH_SIZE_TRAINING, shuffle=True, num_workers=2
)
print(f"  Batches per epoch: {len(loader)}")
print()

if len(dataset) == 0:
    print("ERROR: No sequences built.")
    sys.exit(1)


# ═══════════════════════════════════════════════
# LOAD START CHECKPOINT
# ═══════════════════════════════════════════════
start_path = ckpt_dir / args.start
if not start_path.exists():
    print(f"ERROR: {start_path} not found")
    sys.exit(1)

start_ckpt = torch.load(start_path, map_location=DEVICE)
model      = ARIACoreModel(vocab_size=2304, embed_dim=498)
model.load_state_dict(start_ckpt["model_state"])
model      = model.to(DEVICE)
prev_loss  = start_ckpt["best_loss"]

print(f"Loaded: {args.start}")
print(f"  Loss: {prev_loss:.6f}")
print(f"  Note: {start_ckpt.get('note', '?')}")
print()


# ═══════════════════════════════════════════════
# MASKED TRAINING PASS — saves unconditionally
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

    torch.save({"model_state": best_state, "best_loss": best_loss,
                "pass": pass_name, "note": f"Round 19 — {pass_name}"}, save_path)
    print(f"  Saved: {save_path.name}  loss={best_loss:.6f}")
    print(f"  Pass complete. Best: {best_loss:.6f}")
    print()
    return best_loss, best_state


# ═══════════════════════════════════════════════
# MULTIPASS REWIND
# ═══════════════════════════════════════════════
TARGET      = args.target
floor       = 2.465939
start_total = time.time()

print(f"Starting Round 19 — descent from {prev_loss:.6f}")
print("Farmer logic. Three passes. Two rewinds.")
print()

# ── PASS 1 ─────────────────────────────────────
ep1  = args.epochs_pass1
opt1 = optim.SGD(model.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch1 = torch.optim.lr_scheduler.CosineAnnealingLR(opt1, T_max=ep1, eta_min=1e-7)
loss1, state1 = run_pass(model, loader, ep1, f"PASS 1 — {ep1} epochs",
                          opt1, sch1, TARGET, pass1_path)
if loss1 < floor:
    floor = loss1
    torch.save({"model_state": state1, "best_loss": floor,
                "note": "Round 19 Pass 1 — FLOOR BROKEN"}, word_path)
    print(f"  FLOOR BROKEN: {floor:.6f}")

# ── REWIND 1 ───────────────────────────────────
print(f"Rewinding — {args.epochs_rewind1} epochs...")
model_rw1 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model_rw1.load_state_dict(state1)
erw1    = args.epochs_rewind1
opt_rw1 = optim.SGD(model_rw1.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch_rw1 = torch.optim.lr_scheduler.CosineAnnealingLR(opt_rw1, T_max=erw1, eta_min=1e-7)
_, rewind_state1 = run_pass(model_rw1, loader, erw1, f"REWIND 1 — {erw1} epochs",
                             opt_rw1, sch_rw1, TARGET, rw1_path)

# ── PASS 2 ─────────────────────────────────────
ep2    = args.epochs_pass2
model2 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model2.load_state_dict(rewind_state1)
opt2   = optim.SGD(model2.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch2   = torch.optim.lr_scheduler.CosineAnnealingLR(opt2, T_max=ep2, eta_min=1e-7)
loss2, state2 = run_pass(model2, loader, ep2, f"PASS 2 — {ep2} epochs",
                          opt2, sch2, TARGET, pass2_path)
if loss2 < floor:
    floor = loss2
    torch.save({"model_state": state2, "best_loss": floor,
                "note": "Round 19 Pass 2 — FLOOR BROKEN"}, word_path)
    print(f"  FLOOR BROKEN: {floor:.6f}")

# ── REWIND 2 ───────────────────────────────────
print(f"Rewinding — {args.epochs_rewind2} epochs...")
best_so_far = state2 if loss2 < loss1 else state1
model_rw2   = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model_rw2.load_state_dict(best_so_far)
erw2    = args.epochs_rewind2
opt_rw2 = optim.SGD(model_rw2.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch_rw2 = torch.optim.lr_scheduler.CosineAnnealingLR(opt_rw2, T_max=erw2, eta_min=1e-7)
_, rewind_state2 = run_pass(model_rw2, loader, erw2, f"REWIND 2 — {erw2} epochs",
                             opt_rw2, sch_rw2, TARGET, rw2_path)

# ── PASS 3 ─────────────────────────────────────
ep3    = args.epochs_pass3
model3 = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
model3.load_state_dict(rewind_state2)
opt3   = optim.SGD(model3.parameters(), lr=0.0005, momentum=0.9, weight_decay=1e-4)
sch3   = torch.optim.lr_scheduler.CosineAnnealingLR(opt3, T_max=ep3, eta_min=1e-7)
loss3, state3 = run_pass(model3, loader, ep3, f"PASS 3 — {ep3} epochs",
                          opt3, sch3, TARGET, pass3_path)
if loss3 < floor:
    floor = loss3
    torch.save({"model_state": state3, "best_loss": floor,
                "note": "Round 19 Pass 3 — FLOOR BROKEN"}, word_path)
    print(f"  FLOOR BROKEN: {floor:.6f}")

# ═══════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════
total_time   = time.time() - start_total
overall_best = min(loss1, loss2, loss3)
broke_floor  = overall_best < 2.465939

print()
print("═" * 60)
print()
print(f"Round 19 complete.")
print(f"Time: {total_time/60:.1f} minutes")
print()
print(f"Start:          {prev_loss:.6f}  ({args.start})")
print(f"Pass 1 best:    {loss1:.6f}  -> {pass1_path.name}")
print(f"Pass 2 best:    {loss2:.6f}  -> {pass2_path.name}")
print(f"Pass 3 best:    {loss3:.6f}  -> {pass3_path.name}")
print(f"Overall best:   {overall_best:.6f}")
print(f"Previous floor: 2.465939")
if broke_floor:
    print(f"FLOOR BROKEN.   {overall_best:.6f} < 2.465939")
    print(f"Improvement:    {2.465939 - overall_best:.6f}")
else:
    print(f"Gap remaining:  {overall_best - 2.465939:.6f}")
    print(f"Round 20 loads: {pass3_path.name}  ({loss3:.6f})")
print()
print("NOT standard. NOT scared.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
