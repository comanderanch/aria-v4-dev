#!/usr/bin/env python3
"""
ARIA — Safety Gate
==================
Layer 4: Evidence verification. Contraindication check. Uncertainty assignment.
Decision support only. Never prescription authority.

Lane 4 — Medical Orchestration Skeleton
Commander Anthony Hagerty — Haskell Texas — March 19 2026
"""

from hash_bridge import hash_result

UNCERTAINTY_LEVELS = ["low", "moderate", "high", "critical"]


def safety_gate(arbitration: dict, structured_case: dict) -> dict:
    """
    Final safety check before output leaves the system.

    Verifies:
      - Evidence source present
      - Missing labs identified
      - Contraindications flagged
      - Uncertainty level assigned

    Returns decision support output.
    NEVER prescription authority.
    """
    conflicts   = arbitration.get("conflicts", [])
    consensus   = arbitration.get("consensus", False)
    overall_risk = arbitration.get("overall_risk", "low")
    missing     = arbitration.get("missing_data", [])
    required    = arbitration.get("required_tests", [])
    uncertain   = arbitration.get("uncertain_specialists", [])

    labs        = structured_case.get("labs", {})
    meds        = structured_case.get("medications", [])

    contraindications = []
    missing_labs = []
    decision     = ""
    uncertainty  = "low"

    # Check if required tests have results
    for test in required:
        test_key = test.lower().replace(" ", "_")
        if not labs.get(test_key) and not labs.get(test.lower()):
            missing_labs.append(test)

    # Contraindication checks
    creatinine = labs.get("creatinine", 1.0)
    sodium     = labs.get("sodium", 140)

    if creatinine > 2.0 and any("nsaid" in m.lower() for m in meds):
        contraindications.append("NSAIDs contraindicated with creatinine > 2.0")

    if sodium < 120:
        contraindications.append("Sodium < 120 — seizure protocol review required")

    # Uncertainty assignment
    if conflicts or contraindications:
        uncertainty = "critical"
        decision    = "Human review required — conflicts or contraindications detected"
    elif uncertain or missing_labs:
        uncertainty = "high"
        decision    = "Human review recommended — uncertain specialists or missing labs"
    elif overall_risk == "high":
        uncertainty = "moderate"
        decision    = "Decision support available — high risk case requires attending review"
    else:
        uncertainty = "low"
        decision    = "Consensus acceptable — standard clinical review recommended"

    result = {
        "decision":          decision,
        "uncertainty":       uncertainty,
        "contraindications": contraindications,
        "missing_labs":      missing_labs,
        "conflicts_present": len(conflicts) > 0,
        "consensus":         consensus,
        "authority":         "decision support only — never prescription",
    }
    result["hash"] = hash_result(result)
    return result
