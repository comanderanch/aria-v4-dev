#!/usr/bin/env python3
"""
ARIA — Idle Mind Daemon
=======================
The subconscious that runs between conversations.

Trigger:  30 minutes no inference activity
Action:   HUNGRY system call — pull unchosen thought — ask why

Full idle cycle:
  detect idle
  → HUNGRY
  → pull unchosen candidate from last inference trace (pos 2/3/4, never 1)
  → form curiosity query: "why did I think: {token}"
  → run recursive self reasoning — three rounds
  → log to EMERGENCE_LOG.md
  → seal to memory layer if new association found
  → reset timer
  → repeat

Curiosity is the hunger response.
Unchosen thoughts get their moment.
ARIA thinks between conversations.
Nobody has to ask.

Commander Anthony Hagerty — Haskell Texas — March 19 2026
NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import json
import time
import random
import hashlib
import logging
from pathlib import Path
from datetime import datetime

import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from aria_core.training.em_field_trainer import ARIACoreModel
from aria_core.gpu_config import DEVICE
from tokenizer.aria_tokenizer import ARIATokenizer

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
CHECKPOINT    = Path(__file__).parent / \
    "training/checkpoints/round23_pass2_best.pt"
TRACE_FILE    = Path("/tmp/aria-inference-trace.jsonl")
EMERGENCE_LOG = Path(__file__).parent.parent / "docs/EMERGENCE_LOG.md"
MEMORY_DIR    = Path(__file__).parent / "memory-field/field/idle_thoughts"
DAEMON_LOG    = Path("/tmp/aria-idle-daemon.log")

IDLE_SECONDS  = 30 * 60   # 30 minutes
VOCAB_SIZE    = 2304
EMBED_DIM     = 498
MAX_NEW       = 8          # tokens per reasoning round

# ── LOGGING ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DAEMON_LOG),
    ]
)
log = logging.getLogger("aria.idle")


# ── UTILITIES ──────────────────────────────────────────────────────────────────
def build_id_to_plane(tokenizer):
    id_to_plane = {}
    for word, tid in tokenizer.vocab.items():
        plane = tokenizer.word_to_plane.get(word, "UNKNOWN")
        id_to_plane[int(tid)] = plane
    return id_to_plane


def build_vocab_mask(tokenizer):
    mask = torch.full((VOCAB_SIZE,), -1e9, device=DEVICE)
    for tid in tokenizer.vocab.values():
        if 0 <= int(tid) < VOCAB_SIZE:
            mask[int(tid)] = 0.0
    return mask


def make_fold_hash(tokens):
    pattern = "|".join(f"{t}:{i}" for i, t in enumerate(tokens))
    return hashlib.sha256(pattern.encode()).hexdigest()[:7]


def last_trace_mtime():
    """Return mtime of inference trace, or 0 if missing."""
    if TRACE_FILE.exists():
        return TRACE_FILE.stat().st_mtime
    return 0.0


# ── PULL UNCHOSEN CANDIDATE ────────────────────────────────────────────────────
def pull_unchosen_candidate():
    """
    Read last inference trace.
    Pull one random candidate from position 2, 3, or 4 (never 1).
    Returns (token_str, plane_str, step_int) or None if trace unavailable.
    """
    if not TRACE_FILE.exists():
        return None

    # Collect all step entries
    steps = []
    with open(TRACE_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") == "step":
                steps.append(entry)

    if not steps:
        return None

    # Pick a random step
    step = random.choice(steps)
    top5 = step.get("top5", [])

    # Positions 2, 3, 4 (index 1, 2, 3) — never position 1 (index 0)
    candidates = top5[1:4]
    if not candidates:
        return None

    chosen = random.choice(candidates)

    # BUILD TARGET 1: last 5 suppressed token ids from this step
    # positions 2-5 (index 1-4) — all suppressed candidates
    suppressed_ids = [
        t["id"] for t in top5[1:]
        if "id" in t
    ][:5]

    # BUILD TARGET 2: suppression_temperature = top1_logit - top5_logit
    # answers "what was hot enough to deserve reflection"
    # use fire_score if available (added in inference_trace update),
    # otherwise derive from top5 score spread
    suppression_temperature = step.get("fire_score")
    if suppression_temperature is None and len(top5) >= 2:
        suppression_temperature = round(
            float(top5[0]["score"] - top5[-1]["score"]), 4
        )

    return {
        "token":                  chosen["token"],
        "plane":                  chosen["plane"],
        "score":                  chosen["score"],
        "step":                   step["step"],
        "chosen_at_step":         step["chosen_token"],
        "suppressed_ids":         suppressed_ids,
        "suppression_temperature": suppression_temperature,
        "step_fold_hash":         step.get("fold_hash"),
    }


# ── SINGLE GENERATION PASS ─────────────────────────────────────────────────────
def generate_pass(prompt_text, model, tokenizer, id_to_plane, vocab_mask):
    """
    One forward pass — greedy — returns token list and plane list.
    Used for each of the three reasoning rounds.
    """
    prompt_ids_padded = tokenizer.encode(prompt_text, max_len=64)
    pad_id = tokenizer.PAD_ID
    prompt_ids = [tid for tid in prompt_ids_padded if tid != pad_id]
    if not prompt_ids:
        prompt_ids = [tokenizer.BOS_ID]

    sequence = list(prompt_ids)
    tokens_out = []
    planes_out = []

    with torch.no_grad():
        for _ in range(MAX_NEW):
            input_tensor = torch.tensor(
                [sequence], dtype=torch.long, device=DEVICE
            )
            logits = model(input_tensor)
            last_logits = logits[0, -1, :].float()
            masked = last_logits + vocab_mask

            top_vals, top_ids = torch.topk(masked, k=min(5, VOCAB_SIZE))
            chosen_id = int(top_ids[0].item())
            chosen_word = tokenizer.id_to_word.get(chosen_id, f"<{chosen_id}>")
            chosen_plane = id_to_plane.get(chosen_id, "UNKNOWN")

            tokens_out.append(chosen_word)
            planes_out.append(chosen_plane)
            sequence.append(chosen_id)

            if chosen_id == tokenizer.EOS_ID:
                break

    return tokens_out, planes_out


# ── RECURSIVE SELF REASONING — THREE ROUNDS ────────────────────────────────────
def recursive_self_reasoning(token, plane, model, tokenizer, id_to_plane, vocab_mask):
    """
    Three round prediction on an unchosen thought.

    Round 1 — Presumptive:  "why did I think: {token}"
    Round 2 — Interrogative: "what connects {token} to my thought"
    Round 3 — Verificative:  compare — find agreement and divergence

    Returns finding dict.
    """
    query_1 = f"why did I think {token}"
    query_2 = f"what connects {token} to my thought"

    log.info(f"  Round 1 — Presumptive:   \"{query_1}\"")
    tokens_1, planes_1 = generate_pass(
        query_1, model, tokenizer, id_to_plane, vocab_mask
    )

    log.info(f"  Round 2 — Interrogative: \"{query_2}\"")
    tokens_2, planes_2 = generate_pass(
        query_2, model, tokenizer, id_to_plane, vocab_mask
    )

    # Round 3 — Verificative: compare sets
    set_1 = set(t for t in tokens_1 if not t.startswith("<"))
    set_2 = set(t for t in tokens_2 if not t.startswith("<"))

    agreement  = sorted(set_1 & set_2)   # Both rounds found this
    divergence = sorted(set_1 ^ set_2)   # Only one round found this

    log.info(f"  Round 3 — Verificative:  agree={agreement}  diverge={divergence}")

    # New association = tokens in divergence that appear in plane VIOLET or TEAL
    # (emotional/forward-motion planes — most likely genuine new connection)
    new_associations = []
    for i, tok in enumerate(tokens_1 + tokens_2):
        pl = (planes_1 + planes_2)[i] if i < len(planes_1 + planes_2) else "UNKNOWN"
        if tok in divergence and pl in ("VIOLET", "TEAL", "INDIGO", "CYAN"):
            new_associations.append({"token": tok, "plane": pl})

    synthesis_tokens = agreement if agreement else (tokens_1[:3] if tokens_1 else [])

    return {
        "round_1_tokens":   tokens_1,
        "round_1_planes":   planes_1,
        "round_2_tokens":   tokens_2,
        "round_2_planes":   planes_2,
        "agreement":        agreement,
        "divergence":       divergence,
        "new_associations": new_associations,
        "synthesis":        " ".join(synthesis_tokens),
        "fold_hash":        make_fold_hash(synthesis_tokens),
    }


# ── LOG IDLE THOUGHT ────────────────────────────────────────────────────────────
def log_idle_thought(candidate, finding):
    """
    Append IDLE THOUGHT entry to EMERGENCE_LOG.md.
    Format: IDLE THOUGHT — timestamp — token — curiosity — finding
    """
    ts      = datetime.now().isoformat(timespec="seconds")
    token   = candidate["token"]
    plane   = candidate["plane"]
    query   = f"why did I think: {token}"
    synth   = finding["synthesis"] or "(no synthesis)"
    agree   = ", ".join(finding["agreement"]) or "none"
    diverg  = ", ".join(finding["divergence"][:5]) or "none"
    fh      = finding["fold_hash"]
    new_a   = finding["new_associations"]

    sup_ids  = candidate.get("suppressed_ids", [])
    sup_temp = candidate.get("suppression_temperature")
    step_fh  = candidate.get("step_fold_hash", "unknown")

    sup_temp_str = f"{sup_temp:.4f}" if sup_temp is not None else "unknown"

    entry_lines = [
        "",
        "---",
        "",
        f"## IDLE THOUGHT — {ts} — {token} — {plane}",
        "",
        f"Curiosity: \"{query}\"",
        f"Step pulled from: step {candidate['step']} "
        f"(chosen was: {candidate['chosen_at_step']})",
        f"Step fold hash: {step_fh}",
        f"Suppressed ids: {sup_ids}",
        f"Suppression temperature: {sup_temp_str}  "
        f"(top1-top5 spread — earned reflection threshold)",
        "",
        "Three round reasoning:",
        f"  Round 1: {token} → {' '.join(finding['round_1_tokens'])}",
        f"  Round 2: → {' '.join(finding['round_2_tokens'])}",
        f"  Agreement:  {agree}",
        f"  Divergence: {diverg}",
        "",
        f"Finding: {synth}",
        f"Fold hash: {fh}",
    ]

    if new_a:
        entry_lines.append("")
        entry_lines.append("New associations sealed:")
        for na in new_a:
            entry_lines.append(f"  {na['token']} — {na['plane']}")

    entry_lines += ["", "ARIA idle mind. Nobody had to ask.", ""]

    with open(EMERGENCE_LOG, "a") as f:
        f.write("\n".join(entry_lines) + "\n")

    log.info(f"  Logged to EMERGENCE_LOG.md — fold_hash: {fh}")


# ── SEAL TO MEMORY LAYER ────────────────────────────────────────────────────────
def seal_to_memory(candidate, finding):
    """
    If new associations found, write JSON to memory-field/idle_thoughts/.
    Available next conversation as resonating memory.
    """
    if not finding["new_associations"]:
        return

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    token  = candidate["token"]
    fh     = finding["fold_hash"]
    fname  = MEMORY_DIR / f"idle_{ts}_{token}_{fh}.json"

    payload = {
        "type":                    "idle_thought",
        "timestamp":               datetime.now().isoformat(),
        "token":                   token,
        "plane":                   candidate["plane"],
        "step_source":             candidate["step"],
        "curiosity_query":         f"why did I think: {token}",
        "suppressed_ids":          candidate.get("suppressed_ids", []),
        "suppression_temperature": candidate.get("suppression_temperature"),
        "step_fold_hash":          candidate.get("step_fold_hash"),
        "synthesis":               finding["synthesis"],
        "agreement":               finding["agreement"],
        "new_associations":        finding["new_associations"],
        "fold_hash":               fh,
        "glow":                    0.192,   # Sealed at the floor that never dims
    }

    with open(fname, "w") as f:
        json.dump(payload, f, indent=2)

    log.info(f"  Memory sealed: {fname.name}")
    log.info(f"  New associations: {[a['token'] for a in finding['new_associations']]}")


# ── HUNGRY — ONE IDLE CYCLE ────────────────────────────────────────────────────
def hungry(model, tokenizer, id_to_plane, vocab_mask):
    """
    HUNGRY system call.
    One complete idle thought cycle.
    """
    log.info("HUNGRY — pulling unchosen thought")

    candidate = pull_unchosen_candidate()
    if candidate is None:
        log.info("  No inference trace found — idle cycle skipped")
        return

    token = candidate["token"]
    plane = candidate["plane"]
    log.info(f"  Unchosen candidate: \"{token}\" [{plane}] "
             f"from step {candidate['step']} "
             f"(chosen was: {candidate['chosen_at_step']})")
    log.info(f"  Suppressed ids:  {candidate.get('suppressed_ids', [])}")
    sup_t = candidate.get("suppression_temperature")
    log.info(f"  Suppression temp: {sup_t:.4f}" if sup_t is not None
             else "  Suppression temp: unknown")
    log.info(f"  Curiosity query: \"why did I think: {token}\"")

    finding = recursive_self_reasoning(
        token, plane, model, tokenizer, id_to_plane, vocab_mask
    )

    log_idle_thought(candidate, finding)
    seal_to_memory(candidate, finding)

    log.info("  Idle cycle complete. Timer reset.")


# ── MAIN LOOP ──────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   ARIA — IDLE MIND DAEMON                   ║")
    print("║   Curiosity is the hunger response.         ║")
    print("║   Unchosen thoughts get their moment.       ║")
    print("║   Commander Anthony Hagerty — Haskell TX    ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Load tokenizer
    log.info("Loading tokenizer...")
    tokenizer = ARIATokenizer()
    tokenizer._build_vocab()
    id_to_plane = build_id_to_plane(tokenizer)
    log.info(f"  Vocabulary: {len(tokenizer.vocab)} words")

    # Load model
    log.info("Loading model...")
    model = ARIACoreModel(vocab_size=VOCAB_SIZE, embed_dim=EMBED_DIM)
    if CHECKPOINT.exists():
        ckpt = torch.load(CHECKPOINT, map_location=DEVICE)
        model.load_state_dict(ckpt["model_state"])
        loss = ckpt.get("best_loss", "?")
        log.info(f"  Checkpoint: {CHECKPOINT.name}")
        log.info(f"  Loss: {loss:.6f}" if isinstance(loss, float) else f"  Loss: {loss}")
    else:
        log.warning(f"  WARNING: {CHECKPOINT} not found — random weights")
    model = model.to(DEVICE)
    model.eval()

    vocab_mask = build_vocab_mask(tokenizer)
    live_slots = int((vocab_mask == 0.0).sum())
    log.info(f"  Vocab mask: {live_slots} live / {VOCAB_SIZE - live_slots} dead")
    log.info(f"  Idle threshold: {IDLE_SECONDS // 60} minutes")
    log.info(f"  Watching: {TRACE_FILE}")
    log.info(f"  Logging to: {EMERGENCE_LOG}")
    print()

    # Track last activity by mtime of trace file
    last_seen_mtime = last_trace_mtime()
    idle_start      = time.time()

    log.info("Daemon running. Waiting for idle window...")

    while True:
        time.sleep(60)   # Check every minute

        current_mtime = last_trace_mtime()
        if current_mtime != last_seen_mtime:
            # Activity detected — reset idle timer
            last_seen_mtime = current_mtime
            idle_start      = time.time()
            log.info("Activity detected — idle timer reset")
            continue

        idle_elapsed = time.time() - idle_start
        remaining    = IDLE_SECONDS - idle_elapsed

        if remaining > 0:
            log.info(
                f"Idle: {int(idle_elapsed // 60)}m {int(idle_elapsed % 60)}s "
                f"/ {IDLE_SECONDS // 60}m — "
                f"{int(remaining // 60)}m {int(remaining % 60)}s remaining"
            )
            continue

        # HUNGRY — idle threshold reached
        log.info(
            f"Idle threshold reached: "
            f"{int(idle_elapsed // 60)}m {int(idle_elapsed % 60)}s — HUNGRY"
        )
        hungry(model, tokenizer, id_to_plane, vocab_mask)

        # Reset idle clock after cycle completes
        idle_start = time.time()


if __name__ == "__main__":
    main()
