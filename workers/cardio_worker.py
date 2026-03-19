#!/usr/bin/env python3
"""
ARIA — Cardiology Specialist Worker
====================================
Domain: cardiac findings only.
Receives structured_case.json.
Returns standard specialist schema.
Does NOT see other specialist outputs first — bias prevention.

Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

from _specialist_base import build_finding, aimri_stub

SPECIALTY = "cardiology"


def analyze(structured_case: dict) -> dict:
    """
    Cardiology analysis of structured case.
    Answers inside cardiac domain only.

    STUB: rule-based skeleton.
    WIRE: Lane 2 complete → replace rules with ARIA field inference.
    """
    symptoms    = structured_case.get("symptoms", [])
    labs        = structured_case.get("labs", {})
    history     = structured_case.get("history", [])
    medications = structured_case.get("medications", [])
    case_hash   = structured_case.get("case_hash", "")

    finding   = "no cardiac finding"
    confidence = 0.3
    tests      = []
    risk       = "low"
    suppressed = []

    bnp         = labs.get("bnp", 0)
    sodium      = labs.get("sodium", 140)
    has_chf     = any("chf" in h for h in history)
    has_sob     = "shortness of breath" in symptoms
    on_diuretic = any("furosemide" in m or "lasix" in m for m in medications)

    if has_sob and bnp > 400:
        finding    = "possible fluid overload — elevated BNP with dyspnea"
        confidence = 0.72
        tests      = ["BNP repeat", "echocardiogram", "chest X-ray"]
        risk       = "moderate"
        suppressed = ["arrhythmia", "pericarditis", "pulmonary embolism"]
        if bnp > 800:
            confidence = 0.85
            risk       = "high"

    if has_chf and sodium < 130:
        suppressed.append("hyponatremia secondary to CHF")
        tests.append("BMP repeat")

    if on_diuretic and sodium < 130:
        suppressed.append("diuretic-induced hyponatremia")

    # ARIA plane-color reasoning pressure
    # STUB: replace with real AIMRI read when Lane 2 is proven
    dominant_plane, secondary_plane, sup_temp = aimri_stub(finding)
    # Manual assignment until wired:
    if risk == "high":
        dominant_plane, secondary_plane = "RED_ORANGE", "TEAL"
        sup_temp = 3.5
    elif risk == "moderate":
        dominant_plane, secondary_plane = "TEAL", "BLUE"
        sup_temp = 2.33

    return build_finding(
        specialty              = SPECIALTY,
        finding                = finding,
        confidence             = confidence,
        required_tests         = tests,
        risk                   = risk,
        suppressed             = suppressed,
        suppression_temperature = sup_temp,
        dominant_plane         = dominant_plane,
        secondary_plane        = secondary_plane,
        case_hash              = case_hash,
    )


if __name__ == "__main__":
    import json
    test = {
        "age": 74, "symptoms": ["shortness of breath", "low sodium", "fatigue"],
        "labs": {"sodium": 128, "creatinine": 2.1, "bnp": 890},
        "medications": ["lisinopril", "furosemide"],
        "history": ["chf", "ckd stage 3"],
        "case_hash": "test0000"
    }
    print(json.dumps(analyze(test), indent=2))
