#!/usr/bin/env python3
"""
ARIA — Arbitration Worker
==========================
Layer 3: Receives all specialist outputs (structured fields only).
Detects: agreement zones, conflict zones, confidence gaps, contradictions.
Never receives raw narrative. Never contaminated reasoning.

ARIA plane-color integration:
  Where dominant planes agree  = strong consensus signal
  Where dominant planes conflict = dangerous disagreement
  Where temperature is low     = uncertain specialist — flag

Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

import json
from collections import Counter
from hash_bridge import hash_result, contradiction_signature

# Contradiction keyword pairs — any match = immediate flag
CONTRADICTION_PAIRS = [
    ("increase fluids", "restrict fluids"),
    ("increase fluids", "fluid restriction"),
    ("aggressive diuresis", "iv fluids"),
    ("hold diuretic",  "increase diuretic"),
    ("start antibiotic", "no infectious"),
]


def contradiction_check(results: list) -> list:
    """Check all finding text for known contradiction pairs."""
    contradictions = []
    all_text = " ".join(r.get("finding", "").lower() for r in results)
    for term_a, term_b in CONTRADICTION_PAIRS:
        if term_a in all_text and term_b in all_text:
            contradictions.append(f"CONFLICT: '{term_a}' vs '{term_b}'")
    return contradictions


def plane_agreement(results: list) -> dict:
    """
    Tally dominant planes across all specialist outputs.
    Plane agreement = structural consensus in reasoning pressure.
    """
    plane_counts = Counter(r.get("dominant_plane", "UNKNOWN") for r in results)
    total = len(results)
    dominant = plane_counts.most_common(1)[0][0] if plane_counts else "UNKNOWN"
    agreement_pct = plane_counts[dominant] / total if total > 0 else 0.0
    return {
        "dominant_plane":   dominant,
        "agreement_pct":    round(agreement_pct, 3),
        "plane_tally":      dict(plane_counts),
    }


def confidence_weighted_finding(results: list) -> str:
    """
    Return finding from highest-confidence specialist.
    Weighted by confidence — not just count agreement.
    """
    valid = [r for r in results if r.get("confidence", 0) > 0.4]
    if not valid:
        return "insufficient confidence across all specialists"
    best = max(valid, key=lambda r: r.get("confidence", 0))
    return f"{best['specialty']}: {best['finding']} (confidence {best['confidence']:.2f})"


def low_temperature_specialists(results: list, threshold: float = 1.5) -> list:
    """Flag specialists with low suppression_temperature — uncertain output."""
    return [
        r["specialty"] for r in results
        if r.get("suppression_temperature", 999) < threshold
    ]


def arbitrate(specialist_results: list) -> dict:
    """
    Full arbitration of specialist outputs.
    Input: list of specialist output dicts (structured only).
    Output: arbitration summary with hash.
    """
    contradictions   = contradiction_check(specialist_results)
    plane_agr        = plane_agreement(specialist_results)
    weighted_finding = confidence_weighted_finding(specialist_results)
    uncertain        = low_temperature_specialists(specialist_results)
    missing_data     = []

    # Check for missing required tests across specialists
    all_required = []
    for r in specialist_results:
        all_required.extend(r.get("required_tests", []))
    unique_required = sorted(set(all_required))

    # Confidence gap: any specialist below 0.4 = uncertain
    low_conf = [r["specialty"] for r in specialist_results
                if r.get("confidence", 1.0) < 0.4]
    if low_conf:
        missing_data.append(f"Low confidence specialists: {low_conf}")

    # Risk escalation: if any specialist says high, escalate
    risks = [r.get("risk", "low") for r in specialist_results]
    overall_risk = "high" if "high" in risks else \
                   "moderate" if "moderate" in risks else "low"

    # Plane conflict detection
    planes = [r.get("dominant_plane", "UNKNOWN") for r in specialist_results]
    unique_planes = set(planes)
    plane_conflict = len(unique_planes) > 2  # More than 2 different planes = divergence

    result = {
        "consensus":           len(contradictions) == 0,
        "conflicts":           contradictions,
        "plane_agreement":     plane_agr,
        "plane_conflict":      plane_conflict,
        "weighted_finding":    weighted_finding,
        "overall_risk":        overall_risk,
        "required_tests":      unique_required,
        "missing_data":        missing_data,
        "uncertain_specialists": uncertain,
        "contradiction_signature": contradiction_signature(specialist_results),
        "specialist_count":    len(specialist_results),
    }
    result["hash"] = hash_result(result)
    return result


if __name__ == "__main__":
    # Quick test with stub outputs
    test_results = [
        {"specialty": "cardiology",  "finding": "fluid overload — restrict fluids",
         "confidence": 0.72, "risk": "moderate", "required_tests": ["BNP"],
         "dominant_plane": "TEAL", "suppression_temperature": 2.33},
        {"specialty": "nephrology",  "finding": "ckd exacerbation — aggressive diuresis risks aki",
         "confidence": 0.78, "risk": "moderate", "required_tests": ["BMP"],
         "dominant_plane": "BLUE", "suppression_temperature": 1.8},
        {"specialty": "pharmacology", "finding": "ace + loop diuretic interaction",
         "confidence": 0.80, "risk": "moderate", "required_tests": ["electrolytes"],
         "dominant_plane": "INDIGO", "suppression_temperature": 2.8},
    ]
    print(json.dumps(arbitrate(test_results), indent=2))
