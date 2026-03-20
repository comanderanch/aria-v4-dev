#!/usr/bin/env python3
"""
ARIA — AUTO TRAINER
====================
Commander Anthony Hagerty — Haskell Texas
March 20 2026
Sealed by: CLI Claude (Sonnet 4.6)

Runs rounds 31, 32, 33... automatically in sequence.
Stops when loss drops below TARGET_LOSS.
No CLI needed until it finishes.

Each round:
  - Loads previous round's checkpoint
  - Trains 3 epochs
  - Saves new checkpoint
  - Prints loss
  - If loss < TARGET_LOSS — stops

Run once and walk away:
  python3 aria-core/training/run_training_auto.py

NO RETREAT. NO SURRENDER. 💙🐗
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
sys.path.insert(0, str(Path(__file__).parent.parent))

from aria_core.training.em_field_trainer import ARIACoreModel, EMFieldLoss
from aria_core.gpu_config import DEVICE, BATCH_SIZE_TRAINING
from tokenizer.aria_tokenizer import ARIATokenizer
from aria_core.diagnostics.token_trail import TrailLogger
from aria_core.em_null_coupler import EMNullCoupler

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "null_oscillator",
    Path(__file__).parent.parent / "null_oscillator.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
oscillate          = _mod.oscillate
detect_instability = _mod.detect_instability
attempt_generation = _mod.attempt_generation
_log_to_null_trail = _mod._log_to_null_trail

from aria_core.dual_verifier import watch_floor


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

START_ROUND   = 31       # First round to run
MAX_ROUND     = 60       # Hard ceiling — won't run past this
TARGET_LOSS   = 3.5      # Stop when loss drops below this
EPOCHS        = 3        # Epochs per round
LR_START      = 0.00005  # Learning rate for round 31 — decays each round
LR_MIN        = 0.000005 # Floor — never goes below this

CKPT_DIR = Path(__file__).parent / "checkpoints"

# Learning rate schedule — decays gently each round
def get_lr(round_num):
    decay = 0.92 ** (round_num - START_ROUND)
    return max(LR_MIN, LR_START * decay)


# ═══════════════════════════════════════════════════════════════════════════════
# DATASET — same as round 30 — simple word lookup only
# ═══════════════════════════════════════════════════════════════════════════════

class WordTokenizedDataset(torch.utils.data.Dataset):
    def __init__(self, text, tokenizer, seq_length=64):
        self.seq_length = seq_length
        words     = text.lower().split()
        unk_id    = tokenizer.vocab.get("<UNK>", 2301)
        token_ids = []
        for word in words:
            clean = word.strip(".,!?;:\"'()-[]{}")
            tid   = tokenizer.vocab.get(clean, unk_id)
            if 0 <= tid < 2304:
                token_ids.append(tid)
            else:
                token_ids.append(unk_id)

        self.sequences = []
        stride = seq_length // 2
        for i in range(0, len(token_ids) - seq_length, stride):
            seq = token_ids[i:i + seq_length + 1]
            if len(seq) == seq_length + 1:
                self.sequences.append(seq)

    def __len__(self): return len(self.sequences)

    def __getitem__(self, idx):
        seq = self.sequences[idx]
        return (torch.tensor(seq[:-1], dtype=torch.long),
                torch.tensor(seq[1:],  dtype=torch.long))


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD CORPUS — once — shared across all rounds
# ═══════════════════════════════════════════════════════════════════════════════

def load_corpus():
    training_dir    = Path(__file__).parent
    filtered_corpus = training_dir / "filtered_corpus.txt"
    aria_dir        = training_dir.parent

    if filtered_corpus.exists():
        size_mb = filtered_corpus.stat().st_size / (1024 * 1024)
        print(f"  Corpus: {filtered_corpus.name} ({size_mb:.1f} MB)")
        return filtered_corpus.read_text(encoding='utf-8', errors='replace')

    paths = [
        aria_dir / "ARIA_SEED_STORY.md",
        training_dir / "round2_training_data.md",
        training_dir / "round3_language_data.md",
        training_dir / "round4_conversation_data.md",
    ]
    return "\n\n".join(p.read_text() for p in paths if p.exists())


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE ROUND TRAINER
# ═══════════════════════════════════════════════════════════════════════════════

def run_round(round_num, start_ckpt_path, tokenizer, corpus_text, vocab_mask):
    save_path = CKPT_DIR / f"round{round_num}_best.pt"
    lr        = get_lr(round_num)

    print(f"\n{'='*60}")
    print(f"ROUND {round_num} — lr={lr:.2e} — loading {start_ckpt_path.name}")
    print(f"{'='*60}")

    ckpt      = torch.load(start_ckpt_path, map_location=DEVICE)
    model     = ARIACoreModel(vocab_size=2304, embed_dim=498).to(DEVICE)
    model.load_state_dict(ckpt["model_state"])
    prev_loss = ckpt.get("best_loss", float('inf'))
    print(f"  Start loss: {prev_loss:.6f}")

    dataset = WordTokenizedDataset(corpus_text, tokenizer, seq_length=64)
    loader  = torch.utils.data.DataLoader(
        dataset, batch_size=BATCH_SIZE_TRAINING, shuffle=True,
        num_workers=4, pin_memory=True
    )

    coupler   = EMNullCoupler(excitation_scale=0.001)
    criterion = EMFieldLoss()
    trail     = TrailLogger(round_num=round_num, tokenizer=tokenizer)
    opt       = optim.SGD(model.parameters(), lr=lr, momentum=0.9, weight_decay=1e-4)
    sch       = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS, eta_min=lr*0.1)

    best_loss            = float('inf')
    best_state           = None
    null_confirmed_total = 0
    round_start          = time.time()
    last_inputs = last_targets = last_logits = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss  = 0.0
        n_batches   = 0
        epoch_nulls = 0

        for inputs, targets in loader:
            inputs  = inputs.to(DEVICE)
            targets = targets.to(DEVICE)
            opt.zero_grad()

            null_field           = oscillate("VIOLET", 0.192)
            instability, window  = detect_instability(null_field)
            candidate, rejection = attempt_generation(window, null_field)

            if candidate is not None:
                floor = watch_floor(null_field, action_triggered=True)
                if floor["floor_stable"]:
                    condition_data = {
                        "frequency":   null_field["frequency"],
                        "instability": null_field["instability"],
                        "stabilized":  null_field.get("stabilized_output", 0)
                    }
                    condition_hash = hashlib.sha256(
                        json.dumps(condition_data, sort_keys=True).encode()
                    ).hexdigest()[:7]
                    coupler.receive_null_event(condition_hash, "VIOLET", 0.192)
                    _log_to_null_trail({
                        "epoch":          epoch,
                        "condition_hash": condition_hash,
                        "null_confirmed": True,
                        "wired_to_em":    True,
                        "timestamp":      null_field["timestamp"]
                    })
                    epoch_nulls += 1

            null_events = coupler.drain()
            null_exc    = coupler.total_excitation(null_events)

            with torch.amp.autocast('cuda'):
                logits, states = model(inputs, return_states=True)
                masked         = logits + vocab_mask.unsqueeze(0).unsqueeze(0)
                B, S, V        = masked.shape

                ce_loss = F.cross_entropy(
                    masked.view(B * S, V),
                    targets.view(B * S),
                    ignore_index=tokenizer.vocab.get("<PAD>", 2300)
                )
                _, em_metrics = criterion(logits, targets, states, null_excitation=null_exc)

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

        print(f"  Epoch {epoch}/{EPOCHS} | Loss: {avg_loss:.6f} | "
              f"Nulls: {epoch_nulls} | Best: {best_loss:.6f}{improved}")

        if last_logits is not None:
            trail.log_batch(
                epoch=epoch,
                avg_loss=avg_loss,
                inputs=last_inputs,
                targets=last_targets,
                logits=last_logits,
                current_best=best_loss
            )

    trail.close()

    torch.save({
        "model_state": best_state,
        "best_loss":   best_loss,
        "pass":        f"Round {round_num} — Auto Trainer",
        "null_wired":  null_confirmed_total,
        "vocab_size":  len(tokenizer.vocab),
        "round":       round_num,
    }, save_path)

    elapsed = (time.time() - round_start) / 60
    print(f"\n  Saved: {save_path.name}  loss={best_loss:.6f}  ({elapsed:.1f} min)")
    return best_loss, save_path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — CHAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   ARIA — AUTO TRAINER                       ║")
    print(f"║   Rounds {START_ROUND}–{MAX_ROUND} — stop at loss < {TARGET_LOSS}        ║")
    print("║   Commander Anthony Hagerty — Haskell TX   ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print(f"Target loss: {TARGET_LOSS} (coherent sentences begin here)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load tokenizer and corpus once — reuse every round
    print("Loading tokenizer...")
    tokenizer = ARIATokenizer.load()
    print(f"  Vocabulary: {len(tokenizer.vocab)} tokens")

    vocab_mask = torch.full((2304,), -1e9)
    for token_id in tokenizer.vocab.values():
        if 0 <= token_id < 2304:
            vocab_mask[token_id] = 0.0
    vocab_mask = vocab_mask.to(DEVICE)

    print("Loading corpus...")
    corpus_text = load_corpus()
    print(f"  Corpus loaded.")
    print()

    # Find starting checkpoint
    prev_ckpt = None
    for candidate in [
        CKPT_DIR / f"round{START_ROUND - 1}_best.pt",
        CKPT_DIR / "round30_best.pt",
        CKPT_DIR / "round27_best.pt",
        CKPT_DIR / "best_word_level.pt",
    ]:
        if candidate.exists():
            prev_ckpt = candidate
            break

    if prev_ckpt is None:
        print("ERROR: No starting checkpoint found.")
        sys.exit(1)

    print(f"Starting from: {prev_ckpt.name}")

    # Track overall progress
    round_log = []
    session_start = time.time()

    for round_num in range(START_ROUND, MAX_ROUND + 1):
        loss, ckpt_path = run_round(
            round_num, prev_ckpt, tokenizer, corpus_text, vocab_mask
        )
        round_log.append((round_num, loss))
        prev_ckpt = ckpt_path

        print()
        print(f"  Round {round_num} complete — loss={loss:.6f}")

        if loss <= TARGET_LOSS:
            print()
            print("╔══════════════════════════════════════════════╗")
            print("║   TARGET REACHED                            ║")
            print(f"║   Loss: {loss:.6f} — below {TARGET_LOSS}              ║")
            print("║   Coherent sentences should be forming.     ║")
            print("║   Update aria_idle_daemon.py checkpoint.    ║")
            print("╚══════════════════════════════════════════════╝")
            break
        else:
            print(f"  Still above {TARGET_LOSS} — continuing to round {round_num + 1}...")

    # Final summary
    total_elapsed = (time.time() - session_start) / 60
    print()
    print("=" * 60)
    print("AUTO TRAINER COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {total_elapsed:.1f} min")
    print()
    print("Round log:")
    for rn, rl in round_log:
        marker = " <- TARGET" if rl <= TARGET_LOSS else ""
        print(f"  Round {rn:2d}:  loss={rl:.6f}{marker}")
    print()

    final_loss = round_log[-1][1] if round_log else 0.0
    final_ckpt = CKPT_DIR / f"round{round_log[-1][0]}_best.pt" if round_log else None

    if final_loss <= TARGET_LOSS:
        print(f"NEXT: Update aria_idle_daemon.py — change checkpoint to {final_ckpt.name}")
        print(f"NEXT: Restart aria_core_api.py — she will use new weights automatically")
        print(f"      (aria_core_think.py fallback chain picks up roundXX_best.pt)")
    else:
        print(f"Loss still above {TARGET_LOSS} — run again or add more training data.")

    print()
    print("NO RETREAT. NO SURRENDER. 💙🐗")
