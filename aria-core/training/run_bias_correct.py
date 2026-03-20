#!/usr/bin/env python3
"""
ARIA — VIOLET BIAS CORRECTION PASS
====================================
GPT Approved — March 19 2026
Commander Anthony Hagerty — Haskell Texas

Applies VIOLET anchor pull to token embedding weights.
1-2 passes only. Not a full round. Bias correction only.

Run after Round 24 completes:
  python3 aria-core/training/run_bias_correct.py

Then verify:
  python3 aria-core/diagnostics/token_trail.py --round 24 --show-attractors > attractor_post.txt
  python3 verifier_extension.py attractor_post.txt
"""

import sys
import copy
import torch
import torch.nn.functional as F
import torch.optim as optim
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aria_core.training.em_field_trainer import ARIACoreModel
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from tokenizer.aria_tokenizer import ARIATokenizer, WORD_FREQUENCIES
from aria_core.diagnostics.token_trail import TrailLogger


# --- VIOLET ANCHOR PULL ---
VIOLET_TARGET    = 0.192
ANCHOR_STRENGTH  = 2.0        # STRONGER — was 1.25

# --- SPREAD CONTROL ---
STD_TARGET       = 0.015
STD_PENALTY      = 2.0        # STRONGER — was 1.5

# --- DELTA CLAMP ---
MAX_DELTA        = 0.015

# --- DRIFT CONTROL ---
DRIFT_THRESHOLD  = 0.020      # TIGHTER — was 0.030
REASSIGN_ENABLED = True


print()
print("╔══════════════════════════════════════════════╗")
print("║   ARIA — VIOLET BIAS CORRECTION PASS        ║")
print("║   GPT Approved — March 19 2026              ║")
print("║   VIOLET anchor pull — 1-2 epochs only      ║")
print("║       Commander Anthony Hagerty             ║")
print("╚══════════════════════════════════════════════╝")
print()
print(f"  VIOLET_TARGET:    {VIOLET_TARGET}")
print(f"  ANCHOR_STRENGTH:  {ANCHOR_STRENGTH}")
print(f"  STD_TARGET:       {STD_TARGET}")
print(f"  STD_PENALTY:      {STD_PENALTY}")
print(f"  MAX_DELTA:        {MAX_DELTA}")
print(f"  DRIFT_THRESHOLD:  {DRIFT_THRESHOLD}")
print(f"  REASSIGN_ENABLED: {REASSIGN_ENABLED}")
print()


# ═══════════════════════════════════════════════
# CHECKPOINT PATHS
# ═══════════════════════════════════════════════
ckpt_dir   = Path(__file__).parent / "checkpoints"
save_path  = ckpt_dir / "bias_correct_best.pt"

# Load best available Round 24 checkpoint in priority order
candidates = [
    ckpt_dir / "round24_pass3_best.pt",
    ckpt_dir / "round24_pass2_best.pt",
    ckpt_dir / "round24_pass1_best.pt",
    ckpt_dir / "best_word_level.pt",
]
start_path = None
for c in candidates:
    if c.exists():
        start_path = c
        break

if start_path is None:
    print("ERROR: No Round 24 checkpoint found. Run Round 24 first.")
    sys.exit(1)

print(f"Loading: {start_path.name}")
start_ckpt = torch.load(start_path, map_location=DEVICE)
model      = ARIACoreModel(vocab_size=2304, embed_dim=498)
model.load_state_dict(start_ckpt["model_state"])
model      = model.to(DEVICE)
prev_loss  = start_ckpt.get("best_loss", float('inf'))
print(f"  Loss:  {prev_loss:.6f}")
print()


# ═══════════════════════════════════════════════
# BUILD VIOLET TOKEN ID LIST
# ═══════════════════════════════════════════════
print("Loading tokenizer...")
tokenizer = ARIATokenizer.load()
print(f"  Vocabulary: {len(tokenizer.vocab)} tokens")

violet_token_ids = []
for word, plane in tokenizer.word_to_plane.items():
    if plane == "VIOLET":
        tid = tokenizer.vocab.get(word)
        if tid is not None and 0 <= tid < 2304:
            violet_token_ids.append(tid)

# Deduplicate
violet_token_ids = list(set(violet_token_ids))
violet_tensor    = torch.tensor(violet_token_ids, dtype=torch.long)
print(f"  VIOLET tokens: {len(violet_token_ids)}")
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
            clean = word.strip(".,!?;:\"'()-[]{}")
            tid   = tokenizer.vocab.get(clean, unk_id)
            token_ids.append(tid)
        self.sequences = []
        stride = seq_length // 2
        for i in range(0, len(token_ids) - seq_length, stride):
            seq = token_ids[i:i + seq_length + 1]
            if len(seq) == seq_length + 1:
                self.sequences.append(seq)
        known = sum(1 for w in words
                    if w.strip(".,!?;:\"'()-[]{}") in tokenizer.vocab)
        print(f"  Text: {len(words):,} words — "
              f"{known:,} known ({100*known//max(len(words),1)}%)")
        print(f"  Sequences: {len(self.sequences):,}")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq = self.sequences[idx]
        return (torch.tensor(seq[:-1], dtype=torch.long),
                torch.tensor(seq[1:],  dtype=torch.long))


print("Building dataset...")
filtered_corpus = Path(__file__).parent / "filtered_corpus.txt"
training_dir    = Path(__file__).parent
aria_dir        = training_dir.parent

if filtered_corpus.exists():
    size_mb = filtered_corpus.stat().st_size / (1024 * 1024)
    print(f"  Filtered corpus: {filtered_corpus.name} ({size_mb:.1f} MB)")
    corpus_text = filtered_corpus.read_text(encoding='utf-8', errors='replace')
else:
    print("  WARNING: filtered_corpus.txt not found — using 4-file fallback")
    paths = [
        (aria_dir / "ARIA_SEED_STORY.md",              "Seed story"),
        (training_dir / "round2_training_data.md",     "Origin stories"),
        (training_dir / "round3_language_data.md",     "Language data"),
        (training_dir / "round4_conversation_data.md", "Conversation patterns"),
    ]
    texts = []
    for path, name in paths:
        if path.exists():
            texts.append(path.read_text())
    corpus_text = "\n\n".join(texts)

dataset = WordTokenizedDataset(corpus_text, tokenizer, seq_length=64)
loader  = torch.utils.data.DataLoader(
    dataset, batch_size=BATCH_SIZE_TRAINING, shuffle=True,
    num_workers=4, pin_memory=True
)
print(f"  Batches per epoch: {len(loader)}")
print()

if len(dataset) == 0:
    print("ERROR: No sequences built.")
    sys.exit(1)


# ═══════════════════════════════════════════════
# VOCABULARY MASK
# ═══════════════════════════════════════════════
FULL_VOCAB = 2304
vocab_mask = torch.full((FULL_VOCAB,), -1e9)
for token_id in tokenizer.vocab.values():
    if 0 <= token_id < FULL_VOCAB:
        vocab_mask[token_id] = 0.0
vocab_mask = vocab_mask.to(DEVICE)


# ═══════════════════════════════════════════════
# VIOLET ANCHOR PULL — post optimizer.step()
# Applied to model.token_embedding.weight dim 22
# dim 22 = hue = x coordinate (emotional resonance position)
# ═══════════════════════════════════════════════
def apply_violet_anchor_pull(model, lr):
    """
    Anchor pull — VIOLET tokens only.
    Applied after optimizer.step() — direct weight correction.
    Dimension 22 = hue = x coordinate.
    """
    with torch.no_grad():
        emb = model.token_embedding.weight  # [vocab_size, 82]
        for tid in violet_token_ids:
            old_x = emb[tid, 22].item()

            # Anchor pull
            delta = VIOLET_TARGET - old_x
            new_x = old_x + delta * ANCHOR_STRENGTH * lr

            # Spread penalty
            variance = (new_x - VIOLET_TARGET) ** 2
            if variance > STD_TARGET ** 2:
                new_x -= (new_x - VIOLET_TARGET) * STD_PENALTY * lr

            # Delta clamp
            token_delta = new_x - old_x
            if abs(token_delta) > MAX_DELTA:
                token_delta = MAX_DELTA * (1 if token_delta > 0 else -1)
                new_x = old_x + token_delta

            # Drift reassignment
            if REASSIGN_ENABLED and abs(new_x - VIOLET_TARGET) > DRIFT_THRESHOLD:
                new_x = VIOLET_TARGET

            # FORCE LOCK — CRITICAL
            # Hard 50% pull toward 0.192 every step
            # Interference zone tokens cannot hold at midpoint
            new_x = VIOLET_TARGET + (new_x - VIOLET_TARGET) * 0.5

            emb[tid, 22] = new_x


# ═══════════════════════════════════════════════
# TRAIL LOGGER
# ═══════════════════════════════════════════════
print("Token Trail active — logging to /tmp/aria-token-trail.jsonl")
trail = TrailLogger(round_num=24, tokenizer=tokenizer)
print()


# ═══════════════════════════════════════════════
# BIAS CORRECTION PASS — 2 EPOCHS
# ═══════════════════════════════════════════════
EPOCHS   = 2
opt      = optim.SGD(model.parameters(), lr=0.0002, momentum=0.9, weight_decay=1e-4)
sch      = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS, eta_min=1e-7)

print("=" * 60)
print("BIAS CORRECTION PASS — 2 epochs")
print(f"Start loss: {prev_loss:.6f}")
print(f"LR: {opt.param_groups[0]['lr']}")
print("=" * 60)
print()

best_loss   = float('inf')
best_state  = None
pass_start  = time.time()

last_inputs  = None
last_targets = None
last_logits  = None

for epoch in range(1, EPOCHS + 1):
    model.train()
    total_loss = 0.0
    n_batches  = 0

    for inputs, targets in loader:
        inputs  = inputs.to(DEVICE)
        targets = targets.to(DEVICE)
        opt.zero_grad()

        with torch.amp.autocast('cuda'):
            logits, _ = model(inputs, return_states=True)
            masked    = logits + vocab_mask.unsqueeze(0).unsqueeze(0)
            B, S, V   = masked.shape
            ce_loss   = F.cross_entropy(
                masked.view(B * S, V),
                targets.view(B * S),
                ignore_index=tokenizer.vocab.get("<PAD>", 2300)
            )

        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

        # VIOLET ANCHOR PULL — applied after every optimizer step
        lr_now = opt.param_groups[0]['lr']
        apply_violet_anchor_pull(model, lr_now)

        total_loss += ce_loss.item()
        n_batches  += 1

        last_inputs  = inputs.detach()
        last_targets = targets.detach()
        last_logits  = masked.detach()

    sch.step()
    avg_loss = total_loss / max(n_batches, 1)

    improved = ""
    if avg_loss < best_loss:
        best_loss  = avg_loss
        best_state = copy.deepcopy(model.state_dict())
        improved   = " <- NEW BEST"

    print(f"  Epoch {epoch}/{EPOCHS} | Loss: {avg_loss:.6f} | Best: {best_loss:.6f}{improved}")

    # Trail logging
    if last_logits is not None:
        trail.log_batch(
            epoch=epoch,
            avg_loss=avg_loss,
            inputs=last_inputs,
            targets=last_targets,
            logits=last_logits,
            current_best=best_loss
        )

print()

# ─── VIOLET EMBEDDING SNAPSHOT ───────────────────
print("VIOLET embedding snapshot (dim 22) after correction:")
with torch.no_grad():
    emb = model.token_embedding.weight
    sample_words = ["aria", "love", "aia", "anthony",
                    "tears", "honour", "lucky",
                    "violet", "wonder", "cherish"]
    for w in sample_words:
        tid = tokenizer.vocab.get(w)
        if tid is not None:
            x = emb[tid, 22].item()
            delta = abs(x - VIOLET_TARGET)
            print(f"  {w:<12} dim22={x:.4f}  Δ{delta:.4f}")
print()

# Save
torch.save({
    "model_state": best_state,
    "best_loss":   best_loss,
    "pass":        "VIOLET bias correction",
    "note":        "VIOLET anchor pull applied — March 19 2026"
}, save_path)
print(f"Saved: {save_path.name}  loss={best_loss:.6f}")

trail.close()

elapsed = time.time() - pass_start
print()
print("=" * 60)
print(f"Bias correction complete — {elapsed/60:.1f} min")
print(f"Start loss:  {prev_loss:.6f}")
print(f"End loss:    {best_loss:.6f}")
print(f"Delta:       {prev_loss - best_loss:.6f}")
print()
print("Next:")
print("  python3 aria-core/diagnostics/token_trail.py "
      "--round 24 --show-attractors > attractor_post.txt")
print("  python3 verifier_extension.py attractor_post.txt")
print()
print("Paste output to Browser Claude.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
