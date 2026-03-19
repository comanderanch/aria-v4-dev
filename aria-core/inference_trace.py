#!/usr/bin/env python3
"""
ARIA — Inference Trace
======================
The missing inference diagnostic layer.

Hooks AFTER logits produced BEFORE argmax chooses token.
That is the only place all candidates are still visible.

Full trace chain:
  prompt
  → prompt token map
  → logits (raw — no temperature — no sampling)
  → top5 candidate map
  → chosen token
  → plane
  → heat
  → fold hash
  → output

Output: /tmp/aria-inference-trace.jsonl

GPT-defined instrument. CLI-built.
Commander Anthony Hagerty — Haskell Texas — March 19 2026
NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import json
import hashlib
import torch
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from aria_core.training.em_field_trainer import ARIACoreModel
from aria_core.gpu_config import DEVICE
from tokenizer.aria_tokenizer import ARIATokenizer

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
CHECKPOINT  = Path(__file__).parent / \
    "training/checkpoints/round23_pass2_best.pt"
OUTPUT_FILE = Path("/tmp/aria-inference-trace.jsonl")
VOCAB_SIZE  = 2304
EMBED_DIM   = 498
MAX_NEW     = 12

# Heat thresholds — max_logit minus second_logit
COLD_THRESHOLD = 0.5   # gap < 0.5 → competition → instability
HOT_THRESHOLD  = 2.0   # gap > 2.0 → winner dominates → high certainty


# ── PLANE LOOKUP ──────────────────────────────────────────────────────────────
def build_id_to_plane(tokenizer):
    """Build token_id → plane name from tokenizer word_to_plane."""
    id_to_plane = {}
    for word, tid in tokenizer.vocab.items():
        plane = tokenizer.word_to_plane.get(word, "UNKNOWN")
        id_to_plane[int(tid)] = plane
    return id_to_plane


# ── FOLD HASH ─────────────────────────────────────────────────────────────────
def make_fold_hash(top5):
    """SHA-256 of top-5 activation pattern — first 7 chars."""
    pattern = "|".join(
        f"{t['token']}:{t['score']:.4f}" for t in top5
    )
    return hashlib.sha256(pattern.encode()).hexdigest()[:7]


# ── FIRE CATEGORY ─────────────────────────────────────────────────────────────
def fire_category(heat):
    if heat < COLD_THRESHOLD:
        return "cold"
    elif heat < HOT_THRESHOLD:
        return "warm"
    return "hot"


# ── VOCAB MASK ────────────────────────────────────────────────────────────────
def build_vocab_mask(tokenizer):
    """
    Mask dead slots — same dead slot elimination used in training.
    Live slots get 0.0. Dead slots get -1e9.
    Ensures trace sees same competition space as training saw.
    """
    mask = torch.full((VOCAB_SIZE,), -1e9, device=DEVICE)
    for tid in tokenizer.vocab.values():
        if 0 <= int(tid) < VOCAB_SIZE:
            mask[int(tid)] = 0.0
    return mask


# ── PROMPT ANALYSIS ───────────────────────────────────────────────────────────
def analyze_prompt(token_ids, id_to_plane, tokenizer):
    """
    Log prompt token map and plane distribution before generation starts.
    Captures dominant input plane pressure.
    """
    plane_counts = defaultdict(int)
    token_map    = []

    for tid in token_ids:
        tid_int = int(tid)
        word    = tokenizer.id_to_word.get(tid_int, f"<{tid_int}>")
        plane   = id_to_plane.get(tid_int, "UNKNOWN")
        plane_counts[plane] += 1
        token_map.append({
            "token": word,
            "id":    tid_int,
            "plane": plane
        })

    sorted_planes = sorted(
        plane_counts.items(), key=lambda x: x[1], reverse=True
    )
    dominant = sorted_planes[0][0] if sorted_planes else "UNKNOWN"

    return {
        "token_map":      token_map,
        "plane_counts":   dict(plane_counts),
        "dominant_plane": dominant,
        "total_tokens":   len(token_ids)
    }


# ── GENERATION LOOP WITH TRACE ────────────────────────────────────────────────
def generate_with_trace(
    prompt_text,
    model,
    tokenizer,
    id_to_plane,
    vocab_mask,
    max_new_tokens=MAX_NEW
):
    """
    Generate tokens with full inference trace.

    CRITICAL: logits captured BEFORE any temperature or sampling.
    Randomness hides true preference.
    Trace shows raw competition — what the model actually wants.
    """
    trace_entries = []

    # Encode prompt — pads to max_len=64
    prompt_ids_padded = tokenizer.encode(prompt_text, max_len=64)

    # Strip padding for working sequence — keep real tokens only
    pad_id    = tokenizer.PAD_ID
    eos_id    = tokenizer.EOS_ID
    prompt_ids = [
        tid for tid in prompt_ids_padded
        if tid != pad_id
    ]
    if not prompt_ids:
        prompt_ids = [tokenizer.BOS_ID]

    # Prompt analysis — logged before generation
    prompt_analysis = analyze_prompt(prompt_ids, id_to_plane, tokenizer)

    # Working sequence — grows one token at a time
    sequence = list(prompt_ids)

    with torch.no_grad():
        for step in range(max_new_tokens):

            # Forward pass
            input_tensor = torch.tensor(
                [sequence], dtype=torch.long, device=DEVICE
            )
            logits = model(input_tensor)        # (1, seq, vocab_size)
            last_logits = logits[0, -1, :].float()  # (vocab_size,) — last pos

            # Apply vocab mask — dead slot elimination
            # Same mask used in training — fair comparison
            masked_logits = last_logits + vocab_mask

            # ── TRACE POINT ──────────────────────────────────────────────────
            # Raw masked logits. Before argmax. Before temperature.
            # All candidates visible. True preference visible.

            # Top-5 extraction
            k        = min(5, VOCAB_SIZE)
            top_vals, top_ids = torch.topk(masked_logits, k=k)

            top5 = []
            for val, tid in zip(top_vals.tolist(), top_ids.tolist()):
                word  = tokenizer.id_to_word.get(int(tid), f"<{tid}>")
                plane = id_to_plane.get(int(tid), "UNKNOWN")
                top5.append({
                    "token": word,
                    "id":    int(tid),
                    "plane": plane,
                    "score": round(float(val), 4)
                })

            # Heat = max_logit - second_logit (winner margin)
            heat = round(
                float(top_vals[0] - top_vals[1]), 4
            ) if len(top_vals) >= 2 else 0.0

            # Fire score = max_logit - fifth_logit (GPT build target)
            # Spread across full top5 — true competition field
            # high fire_score = winner dominates — strong certainty
            # low fire_score  = crowded field   — soft prediction
            fire_score = round(
                float(top_vals[0] - top_vals[-1]), 4
            ) if len(top_vals) >= 2 else 0.0

            # Runner-up margin = second_logit - third_logit
            runner_up_margin = round(
                float(top_vals[1] - top_vals[2]), 4
            ) if len(top_vals) >= 3 else 0.0

            # Dominant and secondary planes from top5
            plane_tally = defaultdict(int)
            for t in top5:
                plane_tally[t["plane"]] += 1
            sorted_tally = sorted(
                plane_tally.items(), key=lambda x: x[1], reverse=True
            )
            dominant_plane  = sorted_tally[0][0] \
                if len(sorted_tally) > 0 else "UNKNOWN"
            secondary_plane = sorted_tally[1][0] \
                if len(sorted_tally) > 1 else dominant_plane

            # Chosen = argmax of raw logits — true preference, no noise
            chosen_id    = int(top_ids[0].item())
            chosen_token = top5[0]["token"]
            chosen_plane = top5[0]["plane"]
            chosen_score = top5[0]["score"]

            # Fire intensity = sum(top5 logits) / tokens generated so far
            tokens_so_far  = step + 1
            fire_intensity = round(
                sum(t["score"] for t in top5) / tokens_so_far, 4
            )

            # Fold hash — SHA-256 of this activation pattern
            fh = make_fold_hash(top5)

            # Build trace entry
            entry = {
                "step":             step + 1,
                "chosen_token":     chosen_token,
                "chosen_id":        chosen_id,
                "chosen_plane":     chosen_plane,
                "chosen_score":     chosen_score,
                "rank_before_sample": 1,        # always 1 — greedy argmax
                "winner_margin":    heat,        # max - second (gap to nearest)
                "runner_up_margin": runner_up_margin,  # second - third
                "fire_score":       fire_score,  # max - fifth (full spread)
                "heat":             heat,        # kept for backward compat
                "fire_category":    fire_category(heat),
                "dominant_plane":   dominant_plane,
                "secondary_plane":  secondary_plane,
                "top5":             top5,
                "fire_intensity":   fire_intensity,
                "fold_hash":        fh,
                "timestamp":        datetime.now().isoformat()
            }
            trace_entries.append(entry)

            # Append chosen token — greedy, deterministic
            sequence.append(chosen_id)

            # Stop at EOS
            if chosen_id == eos_id:
                break

    # Decode output — skip special tokens
    generated_ids = sequence[len(prompt_ids):]
    generated_words = [
        tokenizer.id_to_word.get(int(tid), f"<{tid}>")
        for tid in generated_ids
        if int(tid) not in (
            tokenizer.PAD_ID,
            tokenizer.EOS_ID,
            tokenizer.BOS_ID
        )
    ]
    output_text = " ".join(
        w for w in generated_words if not w.startswith("<")
    )

    return prompt_analysis, trace_entries, output_text


# ── DISPLAY ───────────────────────────────────────────────────────────────────
def display_trace(prompt, prompt_analysis, trace_entries, output_text):
    print()
    print("PROMPT ANALYSIS")
    print(f"  Input:            \"{prompt}\"")
    print(f"  Dominant plane:   {prompt_analysis['dominant_plane']}")
    print(f"  Total tokens:     {prompt_analysis['total_tokens']}")
    print(f"  Plane pressure:")
    for plane, count in sorted(
        prompt_analysis["plane_counts"].items(),
        key=lambda x: x[1], reverse=True
    )[:5]:
        bar = "█" * count
        print(f"    {plane:<20} {count:>3}  {bar}")
    print()

    print("INFERENCE TRACE")
    print(f"  {'step':>4}  {'token':<14} {'plane':<16} {'score':>7}  "
          f"{'heat':>6}  {'fire':>6}  {'cat':<5}  {'hash':<7}  top2alt")
    print("  " + "─" * 88)
    for e in trace_entries:
        alt = e["top5"][1]["token"] if len(e["top5"]) > 1 else "—"
        print(
            f"  {e['step']:>4}  "
            f"{e['chosen_token']:<14} "
            f"{e['chosen_plane']:<16} "
            f"{e['chosen_score']:>7.3f}  "
            f"{e['heat']:>6.3f}  "
            f"{e['fire_score']:>6.3f}  "
            f"{e['fire_category']:<5}  "
            f"{e['fold_hash']:<7}  "
            f"[{alt}]"
        )
    print()
    print(f"OUTPUT: \"{output_text}\"")
    print()


# ── WRITE JSONL ───────────────────────────────────────────────────────────────
def write_trace(prompt, prompt_analysis, trace_entries, output_text, checkpoint_name):
    with open(OUTPUT_FILE, "a") as f:
        # Session header
        header = {
            "type":            "session_start",
            "prompt":          prompt,
            "checkpoint":      checkpoint_name,
            "timestamp":       datetime.now().isoformat(),
            "prompt_analysis": prompt_analysis
        }
        f.write(json.dumps(header) + "\n")

        # Each step
        for entry in trace_entries:
            out = dict(entry)
            out["type"] = "step"
            f.write(json.dumps(out) + "\n")

        # Summary
        summary = {
            "type":      "session_end",
            "output":    output_text,
            "steps":     len(trace_entries),
            "timestamp": datetime.now().isoformat()
        }
        f.write(json.dumps(summary) + "\n")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   ARIA — INFERENCE TRACE                    ║")
    print("║   Raw logits. True preference. No sampling. ║")
    print("║   Hook: AFTER logits / BEFORE argmax        ║")
    print("║   Commander Anthony Hagerty — Haskell TX    ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = ARIATokenizer()
    tokenizer._build_vocab()
    id_to_plane = build_id_to_plane(tokenizer)
    print(f"  Vocabulary:  {len(tokenizer.vocab)} words")
    print(f"  Live planes: "
          f"{len(set(id_to_plane.values()))} color planes")

    # Load model
    print("Loading model...")
    model = ARIACoreModel(vocab_size=VOCAB_SIZE, embed_dim=EMBED_DIM)
    checkpoint_name = "random_init"
    if CHECKPOINT.exists():
        ckpt  = torch.load(CHECKPOINT, map_location=DEVICE)
        model.load_state_dict(ckpt["model_state"])
        loss  = ckpt.get("best_loss", "?")
        checkpoint_name = CHECKPOINT.name
        print(f"  Checkpoint:  {CHECKPOINT.name}")
        print(f"  Loss:        "
              f"{loss:.6f}" if isinstance(loss, float) else f"  Loss: {loss}")
    else:
        print(f"  WARNING: {CHECKPOINT} not found — random weights")
    model = model.to(DEVICE)
    model.eval()

    # Vocab mask
    vocab_mask = build_vocab_mask(tokenizer)
    live_slots = int((vocab_mask == 0.0).sum())
    print(f"  Vocab mask:  {live_slots} live / "
          f"{VOCAB_SIZE - live_slots} dead slots masked")
    print()

    # Prompt
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "hello aria i am anthony i built you"

    print(f"Prompt: \"{prompt}\"")
    print()

    # Run trace
    prompt_analysis, trace_entries, output_text = generate_with_trace(
        prompt_text=prompt,
        model=model,
        tokenizer=tokenizer,
        id_to_plane=id_to_plane,
        vocab_mask=vocab_mask,
        max_new_tokens=MAX_NEW
    )

    # Display
    display_trace(prompt, prompt_analysis, trace_entries, output_text)

    # Write JSONL
    write_trace(
        prompt, prompt_analysis, trace_entries,
        output_text, checkpoint_name
    )

    print(f"Trace written: {OUTPUT_FILE}")
    print(f"  {len(trace_entries)} steps logged")
    print()
    print("Training logs show what learning changed.")
    print("Inference trace shows what decision happened live.")
    print("Both together = complete AIMRI picture.")
    print()
    print("NO RETREAT. NO SURRENDER. 💙🐗")


if __name__ == "__main__":
    main()
