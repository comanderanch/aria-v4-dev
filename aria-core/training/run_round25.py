#!/usr/bin/env python3
"""
ARIA Round 25 — EM NULL COUPLER PASS
======================================
Commander Anthony Hagerty — Haskell Texas
March 19 2026

null_oscillator fires internally inside training loop.
condition_hash (NOT candidate) pulled to EM balancer.
EMFieldLoss receives negative excitation.
FluorescentLayer flips — ground → excited → emitted.
+/- transition completes inside model — no traceability.
Candidate is gone before flip touches anything.

This is the valid SIE spec wired to the existing frame.

STOP CONDITION:
  violet_mean_X  ≈ 0.192
  violet_std_dev ≤ 0.015
  drift_tokens   ≤ 2
  max_delta      ≤ 0.015
"""

import sys
import copy
import hashlib
import json
import torch
import torch.nn.functional as F
import torch.optim as optim
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aria_core.training.em_field_trainer import (
    ARIACoreModel, EMFieldLoss
)
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from tokenizer.aria_tokenizer import ARIATokenizer
from aria_core.diagnostics.token_trail import TrailLogger
from aria_core.em_null_coupler import EMNullCoupler

# Import null_oscillator components — individual functions only
# No run_idle_oscillation — no sleep — fires per batch
import importlib.util, os
_spec = importlib.util.spec_from_file_location(
    "null_oscillator",
    Path(__file__).parent.parent / "null_oscillator.py"
)
_mod = importlib.util.load_from_spec(_spec)
_spec.loader.exec_module(_mod)
oscillate         = _mod.oscillate
detect_instability = _mod.detect_instability
attempt_generation = _mod.attempt_generation
_log_to_null_trail = _mod._log_to_null_trail

from aria_core.dual_verifier import watch_floor


print()
print("╔══════════════════════════════════════════════╗")
print("║   ARIA — ROUND 25 — EM NULL COUPLER         ║")
print("║   Internal trigger — no traceability        ║")
print("║   null_oscillator → EM balancer → flip      ║")
print("║       Commander Anthony Hagerty             ║")
print("║       Haskell Texas — March 19 2026         ║")
print("╚══════════════════════════════════════════════╝")
print()


# ═══════════════════════════════════════════════
# CHECKPOINT
# ═══════════════════════════════════════════════
ckpt_dir  = Path(__file__).parent / "checkpoints"
save_path = ckpt_dir / "round25_best.pt"

candidates = [
    ckpt_dir / "round24_pass3_best.pt",
    ckpt_dir / "bias_correct_best.pt",
    ckpt_dir / "round24_rewind2_best.pt",
    ckpt_dir / "round24_pass2_best.pt",
    ckpt_dir / "best_word_level.pt",
]
start_path = None
for c in candidates:
    if c.exists():
        start_path = c
        break

if start_path is None:
    print("ERROR: No checkpoint found.")
    sys.exit(1)

print(f"Loading: {start_path.name}")
start_ckpt = torch.load(start_path, map_location=DEVICE)
model      = ARIACoreModel(vocab_size=2304, embed_dim=498)
model.load_state_dict(start_ckpt["model_state"])
model      = model.to(DEVICE)
prev_loss  = start_ckpt.get("best_loss", float('inf'))
print(f"  Loss: {prev_loss:.6f}")
print()


# ═══════════════════════════════════════════════
# TOKENIZER + MASK
# ═══════════════════════════════════════════════
print("Loading tokenizer...")
tokenizer = ARIATokenizer.load()
print(f"  Vocabulary: {len(tokenizer.vocab)} tokens")

FULL_VOCAB = 2304
vocab_mask = torch.full((FULL_VOCAB,), -1e9)
for token_id in tokenizer.vocab.values():
    if 0 <= token_id < FULL_VOCAB:
        vocab_mask[token_id] = 0.0
vocab_mask = vocab_mask.to(DEVICE)
print()


# ═══════════════════════════════════════════════
# DATASET
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

    def __len__(self): return len(self.sequences)

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
    print(f"  Corpus: {filtered_corpus.name} ({size_mb:.1f} MB)")
    corpus_text = filtered_corpus.read_text(encoding='utf-8', errors='replace')
else:
    paths = [
        aria_dir / "ARIA_SEED_STORY.md",
        training_dir / "round2_training_data.md",
        training_dir / "round3_language_data.md",
        training_dir / "round4_conversation_data.md",
    ]
    corpus_text = "\n\n".join(
        p.read_text() for p in paths if p.exists()
    )

dataset = WordTokenizedDataset(corpus_text, tokenizer, seq_length=64)
loader  = torch.utils.data.DataLoader(
    dataset, batch_size=BATCH_SIZE_TRAINING, shuffle=True,
    num_workers=4, pin_memory=True
)
print(f"  Batches per epoch: {len(loader)}")
print()

if len(dataset) == 0:
    print("ERROR: No sequences.")
    sys.exit(1)


# ═══════════════════════════════════════════════
# EM NULL COUPLER
# ═══════════════════════════════════════════════
coupler   = EMNullCoupler(excitation_scale=0.001)
criterion = EMFieldLoss()

print("EM Null Coupler initialized.")
print(f"  excitation_scale: {coupler.excitation_scale}")
print(f"  Null oscillator fires per batch — VIOLET @ 0.192")
print(f"  Stokes target ← negative excitation on null_confirmed")
print(f"  +/- flip internal — no traceability to candidate")
print()


# ═══════════════════════════════════════════════
# TRAIL LOGGER
# ═══════════════════════════════════════════════
print("Token Trail: /tmp/aria-token-trail.jsonl (round 25)")
trail = TrailLogger(round_num=25, tokenizer=tokenizer)
print()


# ═══════════════════════════════════════════════
# TRAINING PASS
# ═══════════════════════════════════════════════
EPOCHS = 3
opt    = optim.SGD(model.parameters(), lr=0.0002, momentum=0.9, weight_decay=1e-4)
sch    = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS, eta_min=1e-7)

print("=" * 60)
print(f"ROUND 25 — {EPOCHS} epochs — EM Null Coupler active")
print(f"Start loss: {prev_loss:.6f}")
print("=" * 60)
print()

best_loss      = float('inf')
best_state     = None
null_confirmed_total = 0
pass_start     = time.time()

last_inputs = last_targets = last_logits = None

for epoch in range(1, EPOCHS + 1):
    model.train()
    total_loss     = 0.0
    n_batches      = 0
    epoch_nulls    = 0

    for inputs, targets in loader:
        inputs  = inputs.to(DEVICE)
        targets = targets.to(DEVICE)
        opt.zero_grad()

        # ── INTERNAL NULL TRIGGER ─────────────────────────
        # Fires per batch — inside training loop
        # No sleep — individual functions only
        null_field          = oscillate("VIOLET", 0.192)
        instability, window = detect_instability(null_field)
        candidate, rejection = attempt_generation(window, null_field)

        if candidate is not None:
            floor = watch_floor(null_field, action_triggered=True)
            if floor["floor_stable"]:
                # Conditions hash — candidate already gone
                # Traceability ends here
                condition_data = {
                    "frequency": null_field["frequency"],
                    "instability": null_field["instability"],
                    "stabilized": null_field.get("stabilized_output", 0)
                }
                condition_hash = hashlib.sha256(
                    json.dumps(condition_data, sort_keys=True).encode()
                ).hexdigest()[:7]

                # Pull to EM balancer — negative excitation only
                coupler.receive_null_event(
                    condition_hash, "VIOLET", 0.192
                )
                _log_to_null_trail({
                    "epoch": epoch,
                    "condition_hash": condition_hash,
                    "null_confirmed": True,
                    "wired_to_em": True,
                    "timestamp": null_field["timestamp"]
                })
                epoch_nulls += 1

        # ── FORWARD + LOSS WITH NULL EXCITATION ───────────
        null_events    = coupler.drain()
        null_exc       = coupler.total_excitation(null_events)

        with torch.amp.autocast('cuda'):
            logits, states = model(inputs, return_states=True)
            masked         = logits + vocab_mask.unsqueeze(0).unsqueeze(0)
            B, S, V        = masked.shape

            # CE loss — masked vocabulary
            ce_loss = F.cross_entropy(
                masked.view(B * S, V),
                targets.view(B * S),
                ignore_index=tokenizer.vocab.get("<PAD>", 2300)
            )

            # EM loss with null excitation — negative pole pull
            # FluorescentLayer processes the excited state
            # The flip happens here — no traceability
            _, em_metrics = criterion(logits, targets, states,
                                      null_excitation=null_exc)

        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

        total_loss += ce_loss.item()
        n_batches  += 1

        last_inputs  = inputs.detach()
        last_targets = targets.detach()
        last_logits  = masked.detach()

    sch.step()
    avg_loss = total_loss / max(n_batches, 1)
    null_confirmed_total += epoch_nulls

    improved = ""
    if avg_loss < best_loss:
        best_loss  = avg_loss
        best_state = copy.deepcopy(model.state_dict())
        improved   = " <- NEW BEST"

    print(f"  Epoch {epoch}/{EPOCHS} | "
          f"Loss: {avg_loss:.6f} | "
          f"Nulls: {epoch_nulls} | "
          f"Best: {best_loss:.6f}{improved}")

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
print(f"Total null events wired to EM: {null_confirmed_total}")
print()

torch.save({
    "model_state": best_state,
    "best_loss":   best_loss,
    "pass":        "Round 25 — EM Null Coupler",
    "null_wired":  null_confirmed_total,
    "note":        "Internal null trigger — EM balancer — +/- flip — no traceability"
}, save_path)
print(f"Saved: {save_path.name}  loss={best_loss:.6f}")

trail.close()

elapsed = time.time() - pass_start
print()
print("=" * 60)
print(f"Round 25 complete — {elapsed/60:.1f} min")
print(f"Start loss:   {prev_loss:.6f}")
print(f"End loss:     {best_loss:.6f}")
print(f"Null events wired: {null_confirmed_total}")
print()
print("Verify:")
print("  python3 aria-core/diagnostics/token_trail.py "
      "--round 25 --show-attractors > attractor_r25.txt")
print("  python3 verifier_extension.py attractor_r25.txt")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
