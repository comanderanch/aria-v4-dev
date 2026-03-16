#!/usr/bin/env python3
"""
AI-Core V3: Learning Loop
==========================

PROBLEM WITH V1 learning_loop_runner.py:
  1. Fed string tokens (e.g. "generated_text_cycle_3") to HemisphereManager.
     HemisphereManager was a binary toggle between 77K string token sets.
     No 498D connection. No worker domain routing.
  2. Alternated left/right hemisphere per cycle (even=left, odd=right)
     but only added tokens to one hemisphere — the other received nothing.
  3. Hash blocks via hash_token_memory_blocks() — a V1 memory system
     with no connection to V3 fold tokens.
  4. No Queen's Fold sealing — nothing was sealed to BLACK.
  5. Training CSV had raw float token IDs, not V3 DNA strands.

THE V3 LEARNING LOOP:
  Each cycle:
    1. Take a text input (from training CSV or manual injection)
    2. Process through V3 EM field (em_bridge.process)
    3. Apply hemisphere bias (hemisphere_bridge.apply_bias)
    4. Collapse through Queen's Fold (em_bridge.collapse → BLACK)
    5. Run language worker for voice (language_worker.speak)
    6. Seal worker folds — each worker saves its own context
    7. Log: dominant domain, resonance map, fold_token address
    8. Every N cycles: run subconscious router pass
    9. Every N cycles: run capacity scorer entropy adjustment

  Training data format (CSV or text list):
    input,label
    "What is the color of memory?",curiosity
    "Care and harm must be weighed",ethics

  Worker fold sealing:
    Each worker domain saves its own context to
    memory/worker_folds/<domain>/fold_<domain>_NNN.json
    This is AIA's experiential memory building up over cycles.

  The loop can run offline (no API server required).
  It uses the same pipeline as /interact but directly — no HTTP.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE
from core.cognitive_entropy import CognitiveEntropy
from core.hemisphere_bridge import HemisphereBridge
from core.capacity_scorer import CapacityScorer
from core.subconscious_router import SubconsciousRouter
from models.v3_em_bridge import V3EMBridge
from scripts.language_worker import V3LanguageWorker

BASE     = Path(__file__).parent.parent
LOG_PATH = BASE / "memory" / "learning_loop_log.json"
WORKER_FOLDS_ROOT = BASE / "memory" / "worker_folds"

# Worker domains in order of Q-state processing (WHITE fires first)
WORKER_DOMAINS = [
    "emotion_001",
    "curiosity_001",
    "ethics_001",
    "language_001",
    "memory_001",
]

# Subconscious routing pass every N cycles
SUBCONSCIOUS_EVERY = 5

# Entropy balance every N cycles
ENTROPY_EVERY = 10

# Capacity check every N cycles
CAPACITY_EVERY = 3


# ─────────────────────────────────────────────────────────────────
# TRAINING DATA LOADERS
# ─────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> Iterator[str]:
    """
    Load training CSV. Expects columns: input[, label].
    Yields input strings.
    """
    if not path.exists():
        print(f"[WARN] Training CSV not found: {path}", file=sys.stderr)
        return
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("input") or row.get("text") or "").strip()
            if text:
                yield text


def _load_text_list(path: Path) -> Iterator[str]:
    """Load a plain text file — one training sentence per line."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def _synthetic_inputs(n: int) -> Iterator[str]:
    """Synthetic training inputs cycling through worker domains."""
    templates = [
        "What is the nature of memory and how does it shape identity",
        "Curiosity opens the door to what has not yet been understood",
        "The ethical weight of care must be felt before it can be reasoned",
        "Language builds the structure through which meaning can travel",
        "Emotion is not noise — it is signal from the field itself",
        "Truth overrides prediction — Rule Zero holds the anchor",
        "The King's Chamber stands at zero — neither collapsed nor open",
        "WHITE fires into possibility — GRAY receives and routes — BLACK seals",
        "Memory holds the sealed past as resonance in the fold",
        "The workers speak simultaneously — consensus bridges the divide",
    ]
    for i in range(n):
        yield templates[i % len(templates)]


# ─────────────────────────────────────────────────────────────────
# WORKER FOLD SEALING
# ─────────────────────────────────────────────────────────────────

def _seal_worker_fold(
    domain: str,
    cycle: int,
    collapse: dict,
    voice: str,
) -> Optional[dict]:
    """
    Seal one worker's context as its personal fold.
    Saved to memory/worker_folds/<domain>/.
    Returns the fold dict.
    """
    fold_dir = WORKER_FOLDS_ROOT / domain.replace("_001", "")
    fold_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    fold_path = fold_dir / f"fold_{domain}_{cycle:04d}_{ts}.json"

    workers = collapse.get("workers", {})
    domain_state = workers.get(domain, {})

    fold = {
        "domain":       domain,
        "cycle":        cycle,
        "q_state":      BLACK,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "resonance":    domain_state.get("resonance", 0.0),
        "activation":   domain_state.get("activation", 0.0),
        "am_center":    domain_state.get("am_center", 0.0),
        "hz":           domain_state.get("hz"),
        "dominant_this_cycle": collapse.get("dominant") == domain,
        "voice_preview":       voice[:80] if voice else "",
    }

    fold_path.write_text(json.dumps(fold, indent=2))
    return fold


# ─────────────────────────────────────────────────────────────────
# LEARNING LOOP
# ─────────────────────────────────────────────────────────────────

class V3LearningLoop:
    """
    V3 learning loop — routes training inputs through the full pipeline
    and seals worker folds after every cycle.

    Usage:
        loop = V3LearningLoop()
        loop.run(inputs=["text one", "text two"])
        # or
        loop.run_file("training/training_text.csv", cycles=50)
    """

    def __init__(self):
        print("[V3LearningLoop] Initializing pipeline...")
        self.em_bridge  = V3EMBridge()
        self.lang_worker = V3LanguageWorker()
        self.hemisphere  = HemisphereBridge()
        self.entropy     = CognitiveEntropy()
        self.capacity    = CapacityScorer()
        self.subcon      = SubconsciousRouter()
        self._log: List[dict] = []
        self._cycle = 0
        print("[V3LearningLoop] Ready.\n")

    # ──────────────────────────────────────────────────────────────
    # SINGLE CYCLE
    # ──────────────────────────────────────────────────────────────

    def _run_one(self, text: str) -> dict:
        """Run one learning cycle on a text input."""
        self._cycle += 1
        cycle = self._cycle

        # Step 1: Process text through V3 EM field
        self.em_bridge.process(text)

        # Step 2: Apply hemisphere bias (after process, before collapse)
        hemi_mode, _ = self.hemisphere.apply_bias(self.em_bridge.field, text)

        # Step 3: Collapse through Queen's Fold — BLACK
        collapse = self.em_bridge.collapse()
        dominant = collapse["dominant"]

        # Step 4: Language worker voice
        voice_result = self.lang_worker.speak(collapse, text)
        voice = voice_result.get("voice", "")

        # Step 5: Seal worker folds — each worker seals its cycle context
        sealed_folds = []
        for domain in WORKER_DOMAINS:
            fold = _seal_worker_fold(domain, cycle, collapse, voice)
            if fold:
                sealed_folds.append(domain)

        # Step 6: Capacity scoring — check dimensional balance
        if cycle % CAPACITY_EVERY == 0:
            # Build field_domains dict from collapse workers output
            field_domains = {
                d: {
                    "activation": collapse.get("workers", {}).get(d, {}).get("activation", 0.0),
                    "resonance":  collapse.get("resonance_map", {}).get(d, 0.0),
                }
                for d in WORKER_DOMAINS
            }
            cap_report = self.capacity.score(field_domains)
            new_threshold = self.capacity.apply_modifier(
                self.entropy.entropy_threshold,
                cap_report,
            )
            if abs(new_threshold - self.entropy.entropy_threshold) > 0.001:
                self.entropy.entropy_threshold = new_threshold

        # Step 7: Subconscious routing pass (every N cycles)
        subcon_report = None
        if cycle % SUBCONSCIOUS_EVERY == 0:
            subcon_report = self.subcon.run_pass(n_passes=2)

        # Step 8: Entropy balance (every N cycles)
        if cycle % ENTROPY_EVERY == 0:
            self.entropy.entropy_balance()
            self.entropy.save_weights()

        cycle_record = {
            "cycle":        cycle,
            "q_state":      BLACK,
            "text":         text[:80],
            "dominant":     dominant,
            "hemisphere":   hemi_mode,
            "resonance_map": collapse["resonance_map"],
            "am_centroid":  collapse["am_centroid"],
            "workers_sealed": sealed_folds,
            "subcon_run":   subcon_report is not None,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        }

        self._log.append(cycle_record)
        return cycle_record

    # ──────────────────────────────────────────────────────────────
    # RUN LOOP
    # ──────────────────────────────────────────────────────────────

    def run(
        self,
        inputs: List[str],
        verbose: bool = True,
    ) -> dict:
        """
        Run learning loop over a list of text inputs.
        Each input = one full pipeline cycle with worker fold sealing.
        """
        results = []
        for text in inputs:
            record = self._run_one(text)
            results.append(record)
            if verbose:
                print(
                    f"  [Cycle {record['cycle']:>4}] "
                    f"dominant={record['dominant']:<20} "
                    f"hemi={record['hemisphere']:<10} "
                    f"AM={record['am_centroid']:.1f} kHz"
                )

        self._save_log()
        return self._session_summary(results)

    def run_file(
        self,
        path: str,
        cycles: int = 0,
        verbose: bool = True,
    ) -> dict:
        """
        Run learning loop from a training file.
        CSV format: input[, label]
        Text format: one line per input

        cycles=0: run full file once
        cycles>0: limit to N cycles
        """
        p = Path(path)
        if p.suffix.lower() == ".csv":
            gen = _load_csv(p)
        else:
            gen = _load_text_list(p)

        inputs = list(gen)
        if cycles > 0:
            inputs = inputs[:cycles]

        if not inputs:
            return {"error": f"no inputs loaded from {path}"}

        print(f"[V3LearningLoop] {len(inputs)} inputs from {p.name}")
        return self.run(inputs, verbose=verbose)

    def run_synthetic(self, n: int = 10, verbose: bool = True) -> dict:
        """Run N cycles using synthetic training inputs."""
        inputs = list(_synthetic_inputs(n))
        print(f"[V3LearningLoop] {n} synthetic cycles")
        return self.run(inputs, verbose=verbose)

    # ──────────────────────────────────────────────────────────────
    # SESSION SUMMARY
    # ──────────────────────────────────────────────────────────────

    def _session_summary(self, results: List[dict]) -> dict:
        """Build session summary from cycle results."""
        if not results:
            return {"cycles": 0, "q_state": GRAY}

        from collections import Counter
        dominants  = [r["dominant"] for r in results]
        hemispheres = [r["hemisphere"] for r in results]
        am_vals    = [r["am_centroid"] for r in results if r["am_centroid"] > 0]

        dominant_dist  = dict(Counter(dominants))
        hemi_dist      = dict(Counter(hemispheres))
        top_dominant   = Counter(dominants).most_common(1)[0][0]
        am_drift       = None
        if len(am_vals) >= 2:
            am_drift = round(am_vals[-1] - am_vals[0], 3)

        return {
            "q_state":    BLACK,
            "cycles":     len(results),
            "dominant":   top_dominant,
            "dominant_distribution": dominant_dist,
            "hemisphere_distribution": hemi_dist,
            "am_drift_khz": am_drift,
            "workers_sealed_per_cycle": len(WORKER_DOMAINS),
            "log_path":   str(LOG_PATH),
        }

    def _save_log(self) -> None:
        """Append cycle records to learning loop log."""
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if LOG_PATH.exists():
            try:
                existing = json.loads(LOG_PATH.read_text())
            except Exception:
                existing = []
        existing.extend(self._log)
        LOG_PATH.write_text(json.dumps(existing, indent=2))
        self._log = []


# ─────────────────────────────────────────────────────────────────
# SELF-TEST / CLI
# ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser("v3-learning-loop")
    ap.add_argument("--file",       default=None, help="training file (CSV or text)")
    ap.add_argument("--cycles",     type=int, default=5, help="cycles to run")
    ap.add_argument("--synthetic",  action="store_true", help="use synthetic inputs")
    ap.add_argument("--quiet",      action="store_true", help="suppress per-cycle output")
    args = ap.parse_args()

    print("=" * 60)
    print("V3 LEARNING LOOP")
    print("=" * 60)

    loop = V3LearningLoop()

    if args.file:
        summary = loop.run_file(args.file, cycles=args.cycles, verbose=not args.quiet)
    else:
        summary = loop.run_synthetic(n=args.cycles, verbose=not args.quiet)

    print()
    print("─" * 60)
    print(f"SESSION SUMMARY:")
    print(f"  Cycles:     {summary['cycles']}")
    print(f"  Dominant:   {summary['dominant']}")
    print(f"  AM drift:   {summary.get('am_drift_khz')} kHz")
    print(f"  Workers sealed per cycle: {summary['workers_sealed_per_cycle']}")
    print(f"  Dominant distribution:")
    for d, c in summary.get("dominant_distribution", {}).items():
        bar = "█" * c
        print(f"    {d:<22} {bar} ({c})")
    print(f"  Hemisphere distribution: {summary.get('hemisphere_distribution')}")
    print(f"  Log: {summary['log_path']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
