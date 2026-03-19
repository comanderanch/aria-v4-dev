#!/usr/bin/env python3
"""
ARIA — Hash Bridge
==================
Shared hash utilities for all specialist workers.
Every output gets fingerprinted.
Hash proves: this output — this checkpoint — this input — reproducible.

Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

import hashlib
import json
from datetime import datetime


def hash_result(data: dict) -> str:
    """
    SHA-256 of sorted JSON — first 8 chars.
    Deterministic. Same input = same hash. Always.
    """
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def hash_case(structured_case: dict) -> str:
    """Hash of the normalized case — proves same case across all workers."""
    return hash_result(structured_case)


def stamp_output(output: dict, case_hash: str) -> dict:
    """
    Add provenance fields to any worker output.
    case_hash: hash of the input case (proves same case)
    output_hash: hash of this specific output (proves this finding)
    """
    output_hash = hash_result(output)
    return {
        **output,
        "hash":       output_hash,
        "case_hash":  case_hash,
        "timestamp":  datetime.now().isoformat(),
    }


def verify_hash(output: dict) -> bool:
    """
    Verify that an output's hash matches its content.
    Removes hash field, recomputes, compares.
    Returns True if the output is unmodified.
    """
    stored = output.get("hash")
    if not stored:
        return False
    check_data = {k: v for k, v in output.items()
                  if k not in ("hash", "case_hash", "timestamp")}
    return hash_result(check_data) == stored


def contradiction_signature(findings: list) -> str:
    """
    Hash of the full finding set — proves this exact set of
    specialist outputs was presented to arbitration.
    """
    combined = sorted(
        [f.get("finding", "") for f in findings]
    )
    return hashlib.sha256("|".join(combined).encode()).hexdigest()[:8]
