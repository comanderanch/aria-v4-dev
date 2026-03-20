#!/usr/bin/env python3
"""
ARIA — THE ONE FUNCTION
========================
Session 5 — Unification Layer — March 20 2026
Commander Anthony Hagerty — Haskell Texas
Sealed by: CLI Claude (Sonnet 4.6)

ALL execution paths route through here.
Not voice. Not GUI. Not commands. Not network. Not ever.

  def aria_core_think(input_text):
      tokens   = tokenize(input_text)
      state    = run_model(tokens)
      decision = resolve_output(state)
      return decision

If anything bypasses this function:
  State continuity lost.
  Curiosity tracking lost.
  Attractor influence lost.
  System identity lost.

ARIA is a decision system. Not a router.
One mind. One route.

WHAT THIS MODULE CONTAINS:
  aria_core_think()     — the one function — entry point for everything
  _tokenize()           — text → token IDs through color plane routing
  _run_model()          — token IDs → model state → logits
  _resolve_output()     — logits → decision dict (text + plane + freq + gate)
  load_model()          — called once at startup — model lives in memory

IMPORTED BY:
  aria_core_api.py      — Flask /think endpoint
  aria_gui.py           — Kings Chamber (rewired in Session 5)
  aria_voice_client.py  — laptop thin client (rewired in Session 5)
  aria_command_runner.py — curiosity gate lives inside think() now
  aria_network_runner.py — SSH gate lives inside think() now

NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import torch
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from aria_core.training.em_field_trainer import ARIACoreModel
from aria_core.gpu_config import DEVICE
from tokenizer.aria_tokenizer import ARIATokenizer
from aria_core.aria_command_runner import curiosity_gate

# ── LOGGING ─────────────────────────────────────────────────────────────────────
log = logging.getLogger("aria.think")

# ── CONFIGURATION ───────────────────────────────────────────────────────────────
VOCAB_SIZE   = 2304
EMBED_DIM    = 498
TEMPERATURE  = 0.85
MAX_TOKENS   = 40

# Checkpoint — latest round first — fallback chain
CHECKPOINT_CANDIDATES = [
    Path(__file__).parent / "training/checkpoints/round30_best.pt",
    Path(__file__).parent / "training/checkpoints/round27_best.pt",
    Path(__file__).parent / "training/checkpoints/round24_pass3_best.pt",
    Path(__file__).parent / "training/checkpoints/best_word_level.pt",
]

# ── RUNTIME STATE — loaded once — lives here ─────────────────────────────────────
_model     = None
_tokenizer = None
_mask      = None
_checkpoint_name = "none"
_best_loss       = 0.0


# ── LOAD — called once at startup ───────────────────────────────────────────────

def load_model():
    """
    Load model and tokenizer into memory.
    Called once. Everything shares this instance.
    """
    global _model, _tokenizer, _mask, _checkpoint_name, _best_loss

    # Find checkpoint
    ckpt_path = None
    for c in CHECKPOINT_CANDIDATES:
        if c.exists():
            ckpt_path = c
            break

    if ckpt_path is None:
        raise FileNotFoundError("No checkpoint found. Run training first.")

    log.info(f"Loading: {ckpt_path.name}")
    ckpt   = torch.load(ckpt_path, map_location=DEVICE)
    _model = ARIACoreModel(vocab_size=VOCAB_SIZE, embed_dim=EMBED_DIM).to(DEVICE)
    _model.load_state_dict(ckpt["model_state"])
    _model.eval()
    _checkpoint_name = ckpt_path.name
    _best_loss       = ckpt.get("best_loss", 0.0)
    log.info(f"  loss={_best_loss:.6f}  device={DEVICE}")

    _tokenizer = ARIATokenizer.load()
    log.info(f"  vocab={len(_tokenizer.vocab)} tokens")

    # Vocab mask — only allow known token positions
    _mask = torch.full((VOCAB_SIZE,), -1e9, device=DEVICE)
    for tid in _tokenizer.vocab.values():
        if 0 <= tid < VOCAB_SIZE:
            _mask[tid] = 0.0

    log.info("Model ready.")


# ── THE THREE INNER STEPS ────────────────────────────────────────────────────────

def _tokenize(input_text: str) -> torch.Tensor:
    """
    Step 1: Text → token IDs → tensor.
    Words find their color planes.
    """
    words     = input_text.lower().split()
    token_ids = []

    for w in words:
        clean = w.strip(".,!?;:\"'()-[]{}")
        tid   = _tokenizer.vocab.get(clean, _tokenizer.UNK_ID)
        if 0 <= tid < VOCAB_SIZE:
            token_ids.append(tid)
        else:
            token_ids.append(_tokenizer.UNK_ID)

    if not token_ids:
        token_ids = [_tokenizer.UNK_ID]

    return torch.tensor([token_ids], dtype=torch.long, device=DEVICE)


def _run_model(tokens: torch.Tensor) -> list:
    """
    Step 2: Token tensor → generated token IDs.
    The model runs. The field responds.
    """
    ids = tokens
    generated = []

    with torch.no_grad():
        for _ in range(MAX_TOKENS):
            logits, _ = _model(ids, return_states=True)
            last       = logits[0, -1] + _mask
            probs      = torch.softmax(last / TEMPERATURE, dim=-1)
            nxt        = torch.multinomial(probs, 1).item()

            if nxt in (_tokenizer.PAD_ID, _tokenizer.EOS_ID):
                break

            generated.append(nxt)
            ids = torch.cat(
                [ids, torch.tensor([[nxt]], device=DEVICE)], dim=1
            )

    return generated


def _resolve_output(state: list) -> dict:
    """
    Step 3: Generated token IDs → decision dict.
    Unknown tokens filtered — clean output returned.
    Emotional signature of what she said included.
    """
    words = []
    for tid in state:
        word = _tokenizer.id_to_word.get(tid, "")
        if word and not word.startswith("<"):
            words.append(word)

    text = " ".join(words) if words else "..."

    # Emotional signature — what plane did she respond from
    sig = _tokenizer.get_emotional_signature(text)

    return {
        "text":           text,
        "dominant_plane": sig["dominant_plane"],
        "avg_freq":       round(sig["avg_freq"], 4),
        "token_count":    len(words),
        "checkpoint":     _checkpoint_name,
        "loss":           round(_best_loss, 6),
        "timestamp":      datetime.utcnow().isoformat(),
    }


# ── THE ONE FUNCTION ─────────────────────────────────────────────────────────────

def aria_core_think(input_text: str, confirmed: bool = False) -> dict:
    """
    THE ONE FUNCTION.
    All execution paths enter here.

    Args:
        input_text: What was said / sent / typed
        confirmed:  True if user confirmed a CAUTION-level action

    Returns:
        {
            "text":           ARIA's response text
            "dominant_plane": color plane she responded from
            "avg_freq":       emotional frequency of response
            "token_count":    tokens generated
            "checkpoint":     which weights she used
            "loss":           current model loss
            "timestamp":      when this thought happened
            "gate":           curiosity gate result (if command detected)
            "action":         action taken (if any)
        }
    """
    if _model is None:
        load_model()

    # ── STEP 1: TOKENIZE ──────────────────────────────────────────────────────
    tokens = _tokenize(input_text)

    # ── CURIOSITY GATE — command detection ────────────────────────────────────
    # If input looks like a command — route through gate
    # Commands start with known shell prefixes or are structured requests
    gate_result = curiosity_gate(input_text)

    # Non-conversational command detected — handle through gate
    if gate_result["decision"] == "BLOCK":
        return {
            "text":           f"I cannot do that. {gate_result['reason']}",
            "dominant_plane": "GRAY_ZERO",
            "avg_freq":       0.0,
            "token_count":    0,
            "checkpoint":     _checkpoint_name,
            "loss":           round(_best_loss, 6),
            "timestamp":      datetime.utcnow().isoformat(),
            "gate":           gate_result,
            "action":         None,
        }

    # ── STEP 2: RUN MODEL ─────────────────────────────────────────────────────
    state = _run_model(tokens)

    # ── STEP 3: RESOLVE OUTPUT ────────────────────────────────────────────────
    decision = _resolve_output(state)
    decision["gate"]   = gate_result
    decision["action"] = None   # future: populated by command/network runners

    log.info(f"THINK: '{input_text[:40]}' → '{decision['text'][:40]}' "
             f"[{decision['dominant_plane']}]")

    return decision


# ── STANDALONE TEST ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(name)s  %(message)s")

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   ARIA — THE ONE FUNCTION — SELF TEST       ║")
    print("║   All paths. One mind.                     ║")
    print("║   Commander Anthony Hagerty — Haskell TX   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    load_model()
    print()

    tests = [
        "hello aria",
        "i love you",
        "what is the zero point",
        "do you remember me",
        "ls -la",          # command — goes through gate
        "rm -rf /home",    # blocked
    ]

    for t in tests:
        result = aria_core_think(t)
        print(f"Input:  {t}")
        print(f"Output: {result['text']}")
        print(f"Plane:  {result['dominant_plane']}  freq={result['avg_freq']}")
        print(f"Gate:   {result['gate']['decision']}")
        print("─" * 50)
        print()
