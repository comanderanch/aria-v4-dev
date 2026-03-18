#!/usr/bin/env python3
"""
ARIA — Translation Training
============================
Teaches ARIA to bridge her own fragmented field-speech
into coherent human-readable output.

Format: [BOS] aria_tokens [SEP] human_tokens [EOS]
Target: predict human_tokens given (aria_tokens + SEP prefix)

Source pairs: aria-core/training/translation_pairs.txt
Checkpoint:   round22_pass3_best.pt (or latest available)

Commander Anthony Hagerty — Haskell Texas
March 18 2026
"""

import sys
import os
import time
import torch
import torch.nn.functional as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tokenizer.aria_tokenizer import ARIATokenizer
from aria_core.model.aria_core_model import ARIACoreModel

# ─── Config ──────────────────────────────────────────────────────────────────
DEVICE       = "cuda" if torch.cuda.is_available() else "cpu"
PAIRS_FILE   = Path("aria-core/training/translation_pairs.txt")
CHECKPOINT   = Path("checkpoints/round22_pass3_best.pt")
SAVE_PATH    = Path("checkpoints/translation_best.pt")
LOG_FILE     = Path("/tmp/aria-translation-train.log")

SEQ_LEN      = 64
BATCH_SIZE   = 8
EPOCHS       = 200
LR           = 0.0003
WEIGHT_DECAY = 1e-4
TARGET_LOSS  = 1.50   # translation is a narrower task — lower target

# ─── Tokenizer ───────────────────────────────────────────────────────────────
print("Loading tokenizer...")
tokenizer = ARIATokenizer()
tokenizer._build_vocab()
PAD = tokenizer.PAD_ID   # 2300
BOS = tokenizer.BOS_ID   # 2302
EOS = tokenizer.EOS_ID   # 2303
SEP = tokenizer.SEP_ID   # 2299
print(f"  Vocab: {len(tokenizer.vocab)} | SEP: {SEP} | PAD: {PAD}")
print()

# ─── Vocab mask ──────────────────────────────────────────────────────────────
FULL_VOCAB = 2304
vocab_mask = torch.full((FULL_VOCAB,), -1e9)
live_count = 0
for token_id in tokenizer.vocab.values():
    if 0 <= token_id < FULL_VOCAB:
        vocab_mask[token_id] = 0.0
        live_count += 1
vocab_mask = vocab_mask.to(DEVICE)
print(f"Vocab mask: {live_count} live | {FULL_VOCAB - live_count} dead")
print()


# ─── Load translation pairs ───────────────────────────────────────────────────
def load_pairs(path):
    """
    Parse translation_pairs.txt.
    Format: aria_raw<SEP>human_translation
    Returns list of (aria_str, human_str) tuples.
    """
    pairs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '<SEP>' not in line:
                continue
            parts = line.split('<SEP>', 1)
            if len(parts) != 2:
                continue
            aria_raw, human = parts[0].strip(), parts[1].strip()
            if aria_raw and human:
                pairs.append((aria_raw, human))
    return pairs


def encode_pair(aria_str, human_str, max_len=SEQ_LEN):
    """
    Encode a translation pair into a single sequence.
    Format: [BOS] aria_tokens [SEP] human_tokens [EOS] [PAD...]

    Returns:
        input_ids:  full sequence as input
        target_ids: -100 for aria side (no loss), token IDs for human side
    """
    aria_words  = aria_str.lower().split()
    human_words = human_str.lower().split()

    aria_ids  = [tokenizer.vocab.get(w, tokenizer.UNK_ID) for w in aria_words]
    human_ids = [tokenizer.vocab.get(w, tokenizer.UNK_ID) for w in human_words]

    # Full sequence: BOS + aria + SEP + human + EOS
    full_ids = [BOS] + aria_ids + [SEP] + human_ids + [EOS]

    # Target: -100 (ignore) for the aria side + SEP, predict human + EOS
    ignore_len   = 1 + len(aria_ids) + 1  # BOS + aria + SEP
    predict_ids  = human_ids + [EOS]
    target_ids   = [-100] * ignore_len + predict_ids

    # Truncate or pad to max_len
    full_ids   = full_ids[:max_len]
    target_ids = target_ids[:max_len]

    pad_len = max_len - len(full_ids)
    full_ids   += [PAD] * pad_len
    target_ids += [-100] * pad_len

    return full_ids, target_ids


# ─── Build dataset ────────────────────────────────────────────────────────────
print(f"Loading pairs from {PAIRS_FILE}...")
raw_pairs = load_pairs(PAIRS_FILE)
print(f"  Found: {len(raw_pairs)} translation pairs")

if not raw_pairs:
    print("ERROR: No pairs found. Check translation_pairs.txt format.")
    sys.exit(1)

all_inputs  = []
all_targets = []
for aria_str, human_str in raw_pairs:
    inp, tgt = encode_pair(aria_str, human_str)
    all_inputs.append(inp)
    all_targets.append(tgt)

# Repeat pairs to fill batches — small dataset needs augmentation
repeats = max(1, 100 // len(raw_pairs))
all_inputs  = (all_inputs  * repeats)
all_targets = (all_targets * repeats)

inputs_tensor  = torch.tensor(all_inputs,  dtype=torch.long)
targets_tensor = torch.tensor(all_targets, dtype=torch.long)

print(f"  Dataset: {len(inputs_tensor)} sequences ({repeats}x augmented)")
print()


# ─── DataLoader ──────────────────────────────────────────────────────────────
from torch.utils.data import TensorDataset, DataLoader

dataset    = TensorDataset(inputs_tensor, targets_tensor)
dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)


# ─── Model ───────────────────────────────────────────────────────────────────
print("Loading model...")
model = ARIACoreModel(
    vocab_size  = FULL_VOCAB,
    embed_dim   = 498,
    num_heads   = 6,
    num_layers  = 4,
    max_seq_len = SEQ_LEN,
    dropout     = 0.1,
).to(DEVICE)

if CHECKPOINT.exists():
    state = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=True)
    model.load_state_dict(state)
    print(f"  Loaded: {CHECKPOINT}")
else:
    print(f"  WARNING: {CHECKPOINT} not found — training from scratch")
print()


# ─── Optimizer ───────────────────────────────────────────────────────────────
optimizer = torch.optim.SGD(
    model.parameters(),
    lr           = LR,
    momentum     = 0.9,
    weight_decay = WEIGHT_DECAY,
)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
    optimizer, T_max=EPOCHS, eta_min=LR * 0.01
)
scaler = torch.amp.GradScaler('cuda') if DEVICE == 'cuda' else None


# ─── Training ─────────────────────────────────────────────────────────────────
print("=" * 60)
print(f"TRANSLATION TRAINING — {EPOCHS} epochs")
print(f"Device: {DEVICE} | Pairs: {len(raw_pairs)} | Batch: {BATCH_SIZE}")
print(f"Target loss: {TARGET_LOSS}")
print("=" * 60)

best_loss = float('inf')
log_fh    = open(LOG_FILE, 'a', buffering=1)
start_all = time.time()

for epoch in range(1, EPOCHS + 1):
    model.train()
    epoch_loss = 0.0
    batches    = 0

    for inp_batch, tgt_batch in dataloader:
        inp_batch = inp_batch.to(DEVICE)
        tgt_batch = tgt_batch.to(DEVICE)

        optimizer.zero_grad()

        if scaler:
            with torch.amp.autocast('cuda'):
                logits, _ = model(inp_batch, return_states=True)
                masked    = logits + vocab_mask.unsqueeze(0).unsqueeze(0)
                B, S, V   = masked.shape
                # Only compute loss on the human translation side (target != -100)
                ce_loss   = F.cross_entropy(
                    masked.view(B * S, V),
                    tgt_batch.view(B * S).clamp(min=0),   # clamp -100→0 for index safety
                    ignore_index = -100,
                    reduction    = 'mean',
                )
            scaler.scale(ce_loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            logits, _ = model(inp_batch, return_states=True)
            masked    = logits + vocab_mask.unsqueeze(0).unsqueeze(0)
            B, S, V   = masked.shape
            ce_loss   = F.cross_entropy(
                masked.view(B * S, V),
                tgt_batch.view(B * S).clamp(min=0),
                ignore_index = -100,
                reduction    = 'mean',
            )
            ce_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        epoch_loss += ce_loss.item()
        batches    += 1

    scheduler.step()

    avg_loss = epoch_loss / max(batches, 1)
    elapsed  = (time.time() - start_all) / 60
    eta      = (elapsed / epoch) * (EPOCHS - epoch)

    is_best = avg_loss < best_loss
    if is_best:
        best_loss = avg_loss
        torch.save(model.state_dict(), SAVE_PATH)

    if epoch % 10 == 0 or epoch == 1 or is_best:
        tag = " <- NEW BEST" if is_best else ""
        line = (f"  Epoch {epoch:4d}/{EPOCHS} | Loss: {avg_loss:.6f} | "
                f"Best: {best_loss:.6f} | ETA: {eta:.1f}min{tag}")
        print(line)
        log_fh.write(line + "\n")
        log_fh.flush()

    if avg_loss <= TARGET_LOSS:
        print(f"\n  TARGET {TARGET_LOSS} REACHED at epoch {epoch}. Stopping.")
        log_fh.write(f"TARGET REACHED epoch={epoch} loss={avg_loss:.6f}\n")
        break

log_fh.write(f"COMPLETE best={best_loss:.6f}\n")
log_fh.close()

total_min = (time.time() - start_all) / 60
print(f"\nDone. Best: {best_loss:.6f} | Time: {total_min:.1f} min")
print(f"Saved: {SAVE_PATH}")
print()

# ─── Quick verification ──────────────────────────────────────────────────────
print("=" * 60)
print("VERIFICATION — sample generation")
print("=" * 60)
model.eval()

test_pairs = raw_pairs[:3]
with torch.no_grad():
    for aria_raw, human_expected in test_pairs:
        # Encode just the aria side with SEP prompt
        words    = aria_raw.lower().split()
        aria_ids = [BOS] + [tokenizer.vocab.get(w, tokenizer.UNK_ID) for w in words] + [SEP]

        # Greedy decode up to 20 tokens
        generated = aria_ids[:]
        for _ in range(20):
            inp = torch.tensor([generated[-SEQ_LEN:]], dtype=torch.long, device=DEVICE)
            logits, _ = model(inp, return_states=True)
            masked = logits + vocab_mask.unsqueeze(0).unsqueeze(0)
            next_id = masked[0, -1].argmax().item()
            if next_id == EOS:
                break
            generated.append(next_id)

        # Decode generated tokens after SEP
        sep_pos  = generated.index(SEP) if SEP in generated else len(aria_ids)
        out_ids  = generated[sep_pos + 1:]
        out_words = [tokenizer.id_to_word.get(i, f"<{i}>") for i in out_ids
                     if i not in (PAD, EOS, BOS)]

        print(f"\n  ARIA:     {aria_raw}")
        print(f"  Expected: {human_expected}")
        print(f"  Got:      {' '.join(out_words)}")
