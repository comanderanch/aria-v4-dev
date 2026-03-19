#!/usr/bin/env python3
"""
ARIA — Intake Worker
====================
Layer 1: Receives raw case. Normalizes to structured_case.json.
No diagnosis. Normalization only.

Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

import json
from pathlib import Path
from hash_bridge import hash_case


# ── SCHEMA ────────────────────────────────────────────────────────────────────
STRUCTURED_CASE_SCHEMA = {
    "age":         None,
    "symptoms":    [],
    "labs":        {},
    "medications": [],
    "history":     [],
}


def normalize_case(raw_case: dict) -> dict:
    """
    Normalize raw case input to structured_case.json schema.
    No inference. No diagnosis. Normalization only.

    Enforces:
      - age as int or None
      - symptoms as list of lowercase strings
      - labs as dict of {name: value}
      - medications as list of lowercase strings
      - history as list of lowercase strings
    """
    structured = {
        "age": int(raw_case["age"]) if raw_case.get("age") is not None else None,
        "symptoms":    [s.lower().strip() for s in raw_case.get("symptoms", [])],
        "labs":        {k.lower(): v for k, v in raw_case.get("labs", {}).items()},
        "medications": [m.lower().strip() for m in raw_case.get("medications", [])],
        "history":     [h.lower().strip() for h in raw_case.get("history", [])],
    }

    structured["case_hash"] = hash_case(
        {k: v for k, v in structured.items() if k != "case_hash"}
    )
    return structured


def intake(raw_case: dict, output_path: Path = None) -> dict:
    """
    Full intake pipeline.
    Returns structured case. Optionally writes to file.
    """
    structured = normalize_case(raw_case)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(structured, f, indent=2)

    return structured


# ── TEST ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_case = {
        "age": 74,
        "symptoms": ["shortness of breath", "low sodium", "fatigue"],
        "labs": {"sodium": 128, "creatinine": 2.1, "BNP": 890},
        "medications": ["lisinopril", "furosemide"],
        "history": ["CHF", "CKD stage 3"]
    }

    result = intake(test_case)
    print(json.dumps(result, indent=2))
    print(f"\nCase hash: {result['case_hash']}")
    print("Intake normalization complete. No diagnosis made.")
