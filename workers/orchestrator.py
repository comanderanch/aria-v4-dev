#!/usr/bin/env python3
"""
ARIA — Orchestrator
====================
Coordinates full pipeline. Runs all specialists in isolation.
Collects outputs. Passes to arbitration. Passes to safety gate.

Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026

NOTE: Specialists run sequentially here (stub).
WIRE: Lane 2 complete → run in parallel with isolated field reads.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

from intake_worker      import intake
from cardio_worker      import analyze as cardio
from renal_worker       import analyze as renal
from infection_worker   import analyze as infection
from pharm_worker       import analyze as pharm
from neuro_worker       import analyze as neuro
from arbitration_worker import arbitrate
from safety_gate        import safety_gate
from hash_bridge        import hash_result

LOG_DIR = Path(__file__).parent / "logs"


def run_case(raw_case: dict, verbose: bool = True) -> dict:
    """
    Full orchestration pipeline.

    Layer 1: Normalize
    Layer 2: Specialists (isolated — no cross-contamination)
    Layer 3: Arbitrate
    Layer 4: Safety gate
    """
    timestamp = datetime.now().isoformat()

    # ── LAYER 1: INTAKE ───────────────────────────────────────────────
    if verbose:
        print("\n[INTAKE] Normalizing case...")
    structured = intake(raw_case)
    case_hash  = structured["case_hash"]
    if verbose:
        print(f"  Case hash: {case_hash}")

    # ── LAYER 2: SPECIALISTS (isolated — bias prevention) ─────────────
    # Workers do NOT see each other before returning findings.
    if verbose:
        print("\n[SPECIALISTS] Running in isolation...")

    specialist_results = []
    for name, worker_fn in [
        ("cardiology",        cardio),
        ("nephrology",        renal),
        ("infectious_disease", infection),
        ("pharmacology",      pharm),
        ("neurology",         neuro),
    ]:
        if verbose:
            print(f"  {name}...")
        result = worker_fn(structured)
        specialist_results.append(result)
        if verbose:
            print(f"    finding: {result['finding'][:60]}")
            print(f"    confidence: {result['confidence']}  "
                  f"plane: {result['dominant_plane']}  "
                  f"temp: {result['suppression_temperature']}")

    # ── LAYER 3: ARBITRATION ──────────────────────────────────────────
    if verbose:
        print("\n[ARBITRATION] Resolving findings...")
    arb = arbitrate(specialist_results)
    if verbose:
        print(f"  Consensus: {arb['consensus']}")
        if arb["conflicts"]:
            print(f"  CONFLICTS: {arb['conflicts']}")
        print(f"  Overall risk: {arb['overall_risk']}")
        print(f"  Plane agreement: {arb['plane_agreement']['dominant_plane']} "
              f"({arb['plane_agreement']['agreement_pct']:.0%})")

    # ── LAYER 4: SAFETY GATE ──────────────────────────────────────────
    if verbose:
        print("\n[SAFETY GATE] Verifying evidence...")
    gate = safety_gate(arb, structured)
    if verbose:
        print(f"  Decision:    {gate['decision']}")
        print(f"  Uncertainty: {gate['uncertainty']}")
        if gate["contraindications"]:
            print(f"  CONTRAINDICATIONS: {gate['contraindications']}")

    # ── FULL CASE RECORD ──────────────────────────────────────────────
    record = {
        "timestamp":          timestamp,
        "case_hash":          case_hash,
        "structured_case":    structured,
        "specialist_results": specialist_results,
        "arbitration":        arb,
        "safety_gate":        gate,
    }
    record["run_hash"] = hash_result({
        "case_hash":  case_hash,
        "arb_hash":   arb.get("hash"),
        "gate_hash":  gate.get("hash"),
    })

    # Log to file
    log_file = LOG_DIR / f"case_{case_hash}_{timestamp[:10]}.json"
    LOG_DIR.mkdir(exist_ok=True)
    with open(log_file, "w") as f:
        json.dump(record, f, indent=2)
    if verbose:
        print(f"\n[LOG] Written to {log_file.name}")
        print(f"[RUN HASH] {record['run_hash']}")

    return record


# ── TEST CASE ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_case = {
        "age": 74,
        "symptoms": ["shortness of breath", "low sodium", "fatigue"],
        "labs": {"sodium": 128, "creatinine": 2.1, "BNP": 890},
        "medications": ["lisinopril", "furosemide"],
        "history": ["CHF", "CKD stage 3"]
    }

    result = run_case(test_case)
    print(f"\n{'='*60}")
    print(f"FINAL DECISION: {result['safety_gate']['decision']}")
    print(f"UNCERTAINTY:    {result['safety_gate']['uncertainty']}")
    print(f"RUN HASH:       {result['run_hash']}")
    print(f"{'='*60}")
