#!/usr/bin/env python3
"""
ARIA — Pharmacology Specialist Worker
=======================================
Domain: medication interactions, contraindications, dosing.
Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

from _specialist_base import build_finding, aimri_stub

SPECIALTY = "pharmacology"

# Known interaction pairs [med_a, med_b, severity, note]
INTERACTIONS = [
    ("lisinopril", "furosemide", "moderate",
     "ACE inhibitor + loop diuretic — risk of hypotension and hyponatremia"),
    ("lisinopril", "spironolactone", "high",
     "dual RAAS blockade — hyperkalemia risk"),
    ("furosemide", "nsaid", "moderate",
     "NSAIDs reduce diuretic efficacy and may worsen renal function"),
]


def analyze(structured_case: dict) -> dict:
    labs      = structured_case.get("labs", {})
    meds      = structured_case.get("medications", [])
    history   = structured_case.get("history", [])
    case_hash = structured_case.get("case_hash", "")

    finding    = "no critical pharmacological finding"
    confidence = 0.5
    tests      = []
    risk       = "low"
    suppressed = []
    flagged_interactions = []

    meds_lower = [m.lower() for m in meds]
    sodium     = labs.get("sodium", 140)
    creatinine = labs.get("creatinine", 1.0)
    has_ckd    = any("ckd" in h for h in history)

    # Check interaction pairs
    for med_a, med_b, severity, note in INTERACTIONS:
        if any(med_a in m for m in meds_lower) and any(med_b in m for m in meds_lower):
            flagged_interactions.append({
                "pair": f"{med_a} + {med_b}",
                "severity": severity,
                "note": note
            })

    if flagged_interactions:
        top = flagged_interactions[0]
        finding    = f"Drug interaction: {top['pair']} — {top['note']}"
        confidence = 0.80
        risk       = top["severity"]
        tests      = ["serum electrolytes", "renal function panel"]

    # Renal dosing check
    if creatinine > 2.0 and any("lisinopril" in m for m in meds_lower):
        suppressed.append("lisinopril dose reduction required in CKD")
        if finding == "no critical pharmacological finding":
            finding    = "ACE inhibitor use in CKD — dose review required"
            confidence = 0.75
            risk       = "moderate"

    dominant_plane, secondary_plane, sup_temp = aimri_stub(finding)
    if risk in ("high", "moderate"):
        dominant_plane, secondary_plane = "INDIGO", "TEAL"
        sup_temp = 2.8

    result = build_finding(
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
    result["interactions"] = flagged_interactions
    return result
