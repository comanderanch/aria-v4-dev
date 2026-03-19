#!/usr/bin/env python3
"""
ARIA — Infectious Disease Specialist Worker
============================================
Domain: infectious/inflammatory findings only.
Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

from _specialist_base import build_finding, aimri_stub

SPECIALTY = "infectious_disease"


def analyze(structured_case: dict) -> dict:
    symptoms  = structured_case.get("symptoms", [])
    labs      = structured_case.get("labs", {})
    history   = structured_case.get("history", [])
    case_hash = structured_case.get("case_hash", "")

    finding    = "no infectious finding identified"
    confidence = 0.3
    tests      = []
    risk       = "low"
    suppressed = []

    wbc     = labs.get("wbc", 7.0)
    temp    = labs.get("temperature", 37.0)
    crp     = labs.get("crp", 0.0)
    has_sob = "shortness of breath" in symptoms
    fatigue = "fatigue" in symptoms

    if wbc > 11.0 or temp > 38.0 or crp > 10.0:
        finding    = "inflammatory markers elevated — possible infectious etiology"
        confidence = 0.55
        tests      = ["blood culture x2", "urinalysis", "chest X-ray", "procalcitonin"]
        risk       = "moderate"
        suppressed = ["viral syndrome", "autoimmune process", "drug reaction"]

    if has_sob and (wbc > 11.0 or temp > 38.0):
        suppressed.append("pneumonia")
        tests.append("sputum culture")

    if not (wbc > 11.0 or temp > 38.0 or crp > 10.0) and fatigue:
        finding    = "fatigue present — insufficient infectious markers in current labs"
        confidence = 0.25
        tests      = ["CBC with differential", "CRP", "ESR"]

    dominant_plane, secondary_plane, sup_temp = aimri_stub(finding)
    if risk == "moderate":
        dominant_plane, secondary_plane = "CYAN", "GRAY_ZERO"
        sup_temp = 1.5  # Uncertain without more labs

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
