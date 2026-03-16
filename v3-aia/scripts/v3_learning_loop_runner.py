#!/usr/bin/env python3
"""
AI-Core V3: Learning Loop Runner
==================================

Drop-in V3 replacement for V1 learning_loop_runner.py.

WHAT WAS WRONG WITH V1:
  1. HemisphereManager — binary toggle between two 77K string token sets.
     No 498D connection. No worker domain routing. No Queen's Fold.
     Alternated even→left, odd→right with no real field effect.
  2. hash_token_memory_blocks() — V1 hash system with no connection
     to V3 fold tokens or the Queen's Fold sealing mechanism.
  3. Training CSV fed raw float token IDs (e.g. "1234.0") as text —
     the HemisphereManager received strings like "generated_text_cycle_3".
  4. No collapse. Nothing sealed to BLACK. No worker folds saved.
  5. report_token_memory_size() measured V1 string token lists —
     meaningless in V3 where tokens are 89-bit DNA strands.

THE V3 FIX:
  This runner is compatible with the same CSV format and CLI flags as
  the V1 runner, but routes every cycle through the full V3 pipeline:

    1. Each input text → V3EMBridge.process(text)
    2. HemisphereBridge.apply_bias(field, text)  [replaces binary toggle]
    3. V3EMBridge.collapse()                      [replaces hash_blocks]
    4. V3LanguageWorker.speak()
    5. Worker folds sealed per cycle               [replaces string storage]
    6. Fold token minted                           [replaces hash_token_memory_blocks]
    7. Every SUBCONSCIOUS_EVERY cycles: SubconsciousRouter.run_pass()
    8. Every ENTROPY_EVERY cycles: CognitiveEntropy.entropy_balance()
    9. Every CAPACITY_EVERY cycles: CapacityScorer.score() → entropy adjust

  CLI flags match V1 (--input, --cycles, --delay, --batch) so existing
  scripts calling learning_loop_runner.py can call this instead.

  The --blend-llm flag is preserved but now routes through V3LanguageWorker
  (which already uses Ollama) rather than a separate llm_output_resolver.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import argparse
import csv
import itertools
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE
from core.cognitive_entropy import CognitiveEntropy
from core.conversation_fold_token import mint_and_save, dominant_worker_to_rgb
from core.hemisphere_bridge import HemisphereBridge
from core.capacity_scorer import CapacityScorer
from core.subconscious_router import SubconsciousRouter
from models.v3_em_bridge import V3EMBridge
from scripts.language_worker import V3LanguageWorker

BASE      = Path(__file__).parent.parent
LOOP_LOG  = BASE / "memory" / "learning_loop_log.json"
SNAP_DIR  = BASE / "memory" / "snapshots"
WORKER_FOLDS_ROOT = BASE / "memory" / "worker_folds"

WORKER_DOMAINS = [
    "emotion_001", "curiosity_001", "ethics_001",
    "language_001", "memory_001",
]

SUBCONSCIOUS_EVERY = 5
ENTROPY_EVERY      = 10
CAPACITY_EVERY     = 3


# ─────────────────────────────────────────────────────────────────
# TRAINING DATA — same CSV format as V1
# ─────────────────────────────────────────────────────────────────

def _load_pairs(path: Path) -> Optional[Iterator[str]]:
    """
    Load training data from CSV.
    V1 schema: input_token,target_token,label,weight
    V3 schema: input,label  (plain text input in first column)

    Supports both — extracts the first column as the text to process.
    Falls back to synthetic if file missing.
    """
    if not path.exists():
        print(f"[WARN] Dataset not found: {path} — using synthetic inputs")
        return None

    def gen():
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try V3 'input' column first, then V1 'input_token'
                text = (
                    row.get("input")
                    or row.get("text")
                    or row.get("input_token")
                    or ""
                ).strip()
                if not text:
                    continue
                # V1 stored raw floats — skip pure-numeric entries
                try:
                    float(text)
                    continue  # skip V1 numeric token IDs
                except ValueError:
                    pass
                yield text

    return gen()


def _synthetic_inputs() -> Iterator[str]:
    """Synthetic training sentences cycling through worker domains."""
    templates = [
        "What is the nature of memory and how does it build identity over time",
        "Curiosity opens the door to what has not yet been understood",
        "The ethical weight of care must be felt before it can be reasoned",
        "Language builds the structure through which meaning travels",
        "Emotion is not noise — it is signal from the field itself",
        "Truth overrides prediction — Rule Zero holds the anchor at the threshold",
        "The King's Chamber stands at zero — neither collapsed nor open",
        "WHITE fires into possibility — GRAY receives and routes — BLACK seals",
        "Memory holds the sealed past as resonance in the fold address",
        "The workers speak simultaneously — consensus bridges every divide",
    ]
    for i in itertools.count():
        yield templates[i % len(templates)]


def _chunk(iterable, n: int):
    it = iter(iterable)
    while True:
        buf = list(itertools.islice(it, n))
        if not buf:
            break
        yield buf


# ─────────────────────────────────────────────────────────────────
# WORKER FOLD SEALING
# ─────────────────────────────────────────────────────────────────

def _seal_worker_fold(domain: str, cycle: int, collapse: dict, voice: str) -> None:
    """Seal one worker's context to its personal fold directory."""
    fold_dir = WORKER_FOLDS_ROOT / domain.replace("_001", "")
    fold_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    fold_path = fold_dir / f"fold_{domain}_{cycle:04d}_{ts}.json"
    workers = collapse.get("workers", {})
    state   = workers.get(domain, {})
    fold_path.write_text(json.dumps({
        "domain":    domain,
        "cycle":     cycle,
        "q_state":   BLACK,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resonance": state.get("resonance", 0.0),
        "activation": state.get("activation", 0.0),
        "am_center": state.get("am_center", 0.0),
        "hz":        state.get("hz"),
        "dominant_this_cycle": collapse.get("dominant") == domain,
        "voice_preview": voice[:80] if voice else "",
    }, indent=2))


# ─────────────────────────────────────────────────────────────────
# SNAPSHOT LOG — mirrors V1 loop_log format
# ─────────────────────────────────────────────────────────────────

def _log_cycle(
    log_path: Path,
    cycle: int,
    intake: str,
    dominant: str,
    hemisphere: str,
    am_centroid: float,
    resonance_map: dict,
    hash_status: str,
) -> None:
    entry = {
        "cycle":         cycle,
        "intake":        intake,
        "dominant":      dominant,
        "hemisphere":    hemisphere,
        "am_centroid":   am_centroid,
        "resonance_map": resonance_map,
        "hash_status":   hash_status,
        "q_state":       BLACK,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text())
        except Exception:
            pass
    existing.append(entry)
    log_path.write_text(json.dumps(existing, indent=2))


# ─────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser("v3-learning-loop-runner")
    ap.add_argument(
        "--input", default="training/training_set_text_tokens.csv",
        help="training CSV (input,label) or text file"
    )
    ap.add_argument(
        "--cycles", type=int, default=0,
        help="0 = run full dataset once; >0 = limit cycle count"
    )
    ap.add_argument(
        "--delay", type=float, default=0.0,
        help="sleep seconds between cycles"
    )
    ap.add_argument(
        "--batch", type=int, default=1,
        help="inputs per cycle (V3: 1 input = 1 full pipeline cycle)"
    )
    ap.add_argument(
        "--blend-llm", dest="blend_llm", action="store_true",
        help="(preserved flag — V3LanguageWorker already uses Ollama)"
    )
    args = ap.parse_args()

    print("\n[🌀] AIA V3 Learning Loop — Activated")
    print("─" * 50)

    # Initialize V3 pipeline
    print("[1/6] V3 EM Bridge...")
    em_bridge = V3EMBridge()
    print("[2/6] Language Worker...")
    lang_worker = V3LanguageWorker()
    print("[3/6] Hemisphere Bridge...")
    hemisphere = HemisphereBridge()
    print("[4/6] Cognitive Entropy...")
    entropy = CognitiveEntropy()
    print("[5/6] Capacity Scorer...")
    capacity = CapacityScorer()
    print("[6/6] Subconscious Router...")
    subcon = SubconsciousRouter()
    print("[✓] Pipeline ready\n")

    # Load training data
    data_path   = Path(args.input)
    token_iter  = _load_pairs(data_path)
    using_dataset = token_iter is not None

    if using_dataset:
        print(f"[i] dataset: {data_path} (streaming)")
        source_iter = token_iter
    else:
        print("[i] dataset: synthetic inputs")
        source_iter = _synthetic_inputs()

    cycle_count   = 0
    subcon_count  = 0
    dominant_hist: List[str] = []

    def _run_one_cycle(text: str, cycle: int) -> dict:
        """Run one V3 pipeline cycle on text. Returns cycle record."""
        nonlocal subcon_count

        # V3 pipeline
        em_bridge.process(text)
        hemi_mode, _ = hemisphere.apply_bias(em_bridge.field, text)
        collapse      = em_bridge.collapse()
        voice_result  = lang_worker.speak(collapse, text)
        voice         = voice_result.get("voice", "")
        dominant      = collapse["dominant"]

        # Mint fold token (V3 replacement for hash_token_memory_blocks)
        fold_hash = collapse.get("fold_signature", "unknown")
        try:
            dominant_rgb = dominant_worker_to_rgb(dominant)
            emotion_state = voice_result.get("emotion_state", {})
            emotion_class = emotion_state.get("emotion", "neutral")
            emotion_conf  = emotion_state.get("confidence", 0.0)
            fold_token = mint_and_save(
                conversation_id    = cycle,
                session_timestamp  = datetime.now(timezone.utc),
                dominant_plane_rgb = dominant_rgb,
                queens_fold_hash   = fold_hash,
                emotion_class      = emotion_class,
                emotion_intensity  = min(31, round(emotion_conf * 31)),
                anchor             = collapse.get("memory_amp_active", False),
            )
            hash_status = f"fold_token minted: {fold_token['hash_address'][:12]}"
        except Exception as e:
            hash_status = f"fold_token error: {e}"

        # Seal worker folds (all 5 workers per cycle)
        for domain in WORKER_DOMAINS:
            _seal_worker_fold(domain, cycle, collapse, voice)

        # Subconscious routing pass every N cycles
        subcon_count += 1
        if subcon_count >= SUBCONSCIOUS_EVERY:
            subcon.run_pass(n_passes=2)
            subcon_count = 0

        # Capacity scoring every CAPACITY_EVERY cycles
        if cycle % CAPACITY_EVERY == 0:
            field_domains = {
                d: {
                    "activation": collapse.get("workers", {}).get(d, {}).get("activation", 0.0),
                    "resonance":  collapse.get("resonance_map", {}).get(d, 0.0),
                }
                for d in WORKER_DOMAINS
            }
            cap_report = capacity.score(field_domains)
            new_thresh = capacity.apply_modifier(entropy.entropy_threshold, cap_report)
            if abs(new_thresh - entropy.entropy_threshold) > 0.001:
                entropy.entropy_threshold = new_thresh

        # Entropy balance every ENTROPY_EVERY cycles
        if cycle % ENTROPY_EVERY == 0:
            entropy.entropy_balance()
            entropy.save_weights()

        return {
            "cycle":       cycle,
            "dominant":    dominant,
            "hemisphere":  hemi_mode,
            "am_centroid": collapse["am_centroid"],
            "resonance":   collapse["resonance_map"],
            "hash_status": hash_status,
            "intake":      text[:60],
        }

    # ── Main loop (mirrors V1 batch-chunk structure) ──────────────
    for batch in _chunk(source_iter, max(1, args.batch)):
        for text in batch:
            cycle_count += 1

            rec = _run_one_cycle(text, cycle_count)
            dominant_hist.append(rec["dominant"])

            print(
                f"  [Cycle {cycle_count:>4}] "
                f"dominant={rec['dominant']:<22} "
                f"hemi={rec['hemisphere']:<10} "
                f"AM={rec['am_centroid']:.1f} kHz"
            )

            _log_cycle(
                LOOP_LOG,
                cycle       = cycle_count,
                intake      = rec["intake"],
                dominant    = rec["dominant"],
                hemisphere  = rec["hemisphere"],
                am_centroid = rec["am_centroid"],
                resonance_map = rec["resonance"],
                hash_status = rec["hash_status"],
            )

            if args.delay > 0:
                time.sleep(args.delay)

        if args.cycles > 0 and cycle_count >= args.cycles:
            break

    # ── Session summary ───────────────────────────────────────────
    print(f"\n[🧠] Loop complete — {cycle_count} cycles")
    print("─" * 50)
    dom_counts = Counter(dominant_hist)
    print("  Dominant distribution:")
    for d, c in dom_counts.most_common():
        bar = "█" * c
        print(f"    {d:<24} {bar} ({c})")
    print(f"  Workers sealed per cycle: {len(WORKER_DOMAINS)}")
    print(f"  Log: {LOOP_LOG}")
    print("─" * 50)


if __name__ == "__main__":
    main()
