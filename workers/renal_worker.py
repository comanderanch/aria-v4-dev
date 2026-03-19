#!/usr/bin/env python3
"""
ARIA — Nephrology Specialist Worker
=====================================
Domain: renal/kidney findings only.
Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

from _specialist_base import build_finding, aimri_stub

SPECIALTY = "nephrology"


def analyze(structured_case: dict) -> dict:
    symptoms  = structured_case.get("symptoms", [])
    labs      = structured_case.get("labs", {})
    history   = structured_case.get("history", [])
    meds      = structured_case.get("medications", [])
    case_hash = structured_case.get("case_hash", "")

    finding    = "no renal finding"
    confidence = 0.3
    tests      = []
    risk       = "low"
    suppressed = []

    creatinine = labs.get("creatinine", 1.0)
    sodium     = labs.get("sodium", 140)
    has_ckd    = any("ckd" in h for h in history)
    on_ace     = any("lisinopril" in m or "enalapril" in m for m in meds)
    on_loop    = any("furosemide" in m or "lasix" in m for m in meds)

    if creatinine > 2.0 and has_ckd:
        finding    = "CKD exacerbation — elevated creatinine on known CKD baseline"
        confidence = 0.78
        tests      = ["BMP", "urine creatinine", "renal ultrasound"]
        risk       = "moderate"
        suppressed = ["acute kidney injury", "contrast nephropathy"]

    if sodium < 130:
        if on_loop and on_ace:
            suppressed.append("medication-induced hyponatremia — ACE + loop diuretic")
            tests.append("spot urine sodium")
        finding = finding + " — hyponatremia present" if finding != "no renal finding" \
            else "hyponatremia — evaluate cause"
        confidence = max(confidence, 0.65)
        risk = "moderate"

    # NOTE: Renal and cardiology will CONFLICT on fluid management.
    # Cardio: may need fluid restriction for overload.
    # Renal: aggressive diuresis risks further AKI.
    # Arbitration must flag this contradiction.
    suppressed.append("fluid restriction conflict with cardiology pending")

    dominant_plane, secondary_plane, sup_temp = aimri_stub(finding)
    if risk == "moderate":
        dominant_plane, secondary_plane = "BLUE", "INDIGO"
        sup_temp = 1.8  # Lower certainty — complex interplay

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
