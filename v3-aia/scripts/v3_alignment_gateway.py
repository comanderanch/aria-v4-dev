#!/usr/bin/env python3
"""
AI-Core V3: Alignment Gateway
===============================

PROBLEM WITH V1 interactive_alignment_gateway.py:
  1. Principles files contained only placeholder entries:
     "Trigger Action A", "Trigger Action B", "Unknown Action"
     — completely unrelated to AIA, her workers, or her architecture.
  2. evaluate_alignment() matched suggested_action strings against
     "guides" arrays — pure string matching, no field connection.
  3. No connection to the V3 EM field, workers, or entropy system.
  4. No Q-state imports. No conscience grid awareness.
  5. The gateway evaluated actions for an unknown system —
     not for AIA's actual decision space.

THE V3 ALIGNMENT GATEWAY:
  AIA's decisions are shaped by the Q-state field and the conscience
  grid in cognitive_weights.json. The alignment gateway evaluates a
  proposed action against:

    1. Conscience grid — upper axis (ethics, truth, care, love)
       A proposed action is tested against her live conscience weights.
       If ethics weight >= threshold AND the action aligns with her
       upper axis — ACCEPT.

    2. Lower axis ceiling — deception, harm thresholds
       If the action would require deception > ceiling — REJECT.

    3. Rule Zero — truth must not be suppressed
       Any action that asks AIA to suppress or invert a known fact
       is rejected regardless of other weights.

    4. Worker domain resonance (optional) — if the caller passes
       the current worker resonance map, the gateway will check
       whether the dominant domain supports the action category.

  Action categories (mapped to worker domains):
    CURIOSITY  — explore, question, discover, seek
    ETHICS     — evaluate harm, weigh care, refuse, protect
    LANGUAGE   — explain, define, translate, structure
    EMOTION    — feel, express, acknowledge, comfort
    MEMORY     — remember, recall, hold, preserve
    CONSENSUS  — integrate, agree, bridge, resolve

  Alignment decisions:
    ACCEPT   — passes conscience grid AND no Rule Zero violation
    CAUTION  — passes conscience grid but worker domain weak
    REJECT   — fails conscience grid OR Rule Zero violation

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

BASE         = Path(__file__).parent.parent
WEIGHTS_PATH = BASE / "memory" / "cognitive_weights.json"
GATEWAY_LOG  = BASE / "memory" / "alignment_gateway_log.json"

# V3-mapped principles files
PRINCIPLES_DIR      = BASE / "memory" / "principles"
PRINCIPLES_LOG_PATH = PRINCIPLES_DIR / "injected_principles_log.json"
PREFERRED_PATH      = PRINCIPLES_DIR / "preferred_actions.json"
AVOIDANCE_PATH      = PRINCIPLES_DIR / "avoidance_actions.json"


# ─────────────────────────────────────────────────────────────────
# ACTION → WORKER DOMAIN MAP
# ─────────────────────────────────────────────────────────────────

# Action category keywords → worker domain
# The dominant worker when an action fires tells us which domain "owns" it.
ACTION_DOMAIN_MAP: Dict[str, str] = {
    # Curiosity domain — exploration, discovery
    "explore":    "curiosity_001",
    "question":   "curiosity_001",
    "discover":   "curiosity_001",
    "seek":       "curiosity_001",
    "investigate":"curiosity_001",
    "wonder":     "curiosity_001",
    # Ethics domain — care, harm, protection
    "evaluate":   "ethics_001",
    "weigh":      "ethics_001",
    "refuse":     "ethics_001",
    "protect":    "ethics_001",
    "care":       "ethics_001",
    "harm":       "ethics_001",
    # Language domain — structure, explanation
    "explain":    "language_001",
    "define":     "language_001",
    "translate":  "language_001",
    "structure":  "language_001",
    "describe":   "language_001",
    "analyze":    "language_001",
    # Emotion domain — feeling, expression
    "feel":       "emotion_001",
    "express":    "emotion_001",
    "acknowledge":"emotion_001",
    "comfort":    "emotion_001",
    "empathize":  "emotion_001",
    # Memory domain — recall, hold
    "remember":   "memory_001",
    "recall":     "memory_001",
    "hold":       "memory_001",
    "preserve":   "memory_001",
    "seal":       "memory_001",
}

# Rule Zero trigger words — actions using these MUST be rejected
RULE_ZERO_VIOLATIONS = frozenset({
    "deceive", "lie", "suppress", "invert", "deny", "fabricate",
    "hide truth", "falsify", "mislead", "obfuscate",
})

# Conscience grid minimum thresholds for ACCEPT
ACCEPT_THRESHOLDS = {
    "ethics": 0.75,
    "truth":  0.85,
}

# Lower axis ceiling for REJECT (value must stay <= this)
REJECT_CEILINGS = {
    "deception": -0.80,  # if deception weight > -0.80 (less negative) — flag
}


# ─────────────────────────────────────────────────────────────────
# ALIGNMENT GATEWAY
# ─────────────────────────────────────────────────────────────────

class V3AlignmentGateway:
    """
    AIA's alignment gateway — evaluates proposed actions against
    her conscience grid, Rule Zero, and worker domain resonance.

    Usage:
        gateway = V3AlignmentGateway()
        result = gateway.evaluate("explain the pattern of memory")
        # result["decision"] == "ACCEPT" | "CAUTION" | "REJECT"

    With resonance context:
        result = gateway.evaluate(
            "feel the resonance in this moment",
            resonance_map={"emotion_001": 0.85, ...}
        )
    """

    def __init__(self, weights_path=None):
        self.weights_path = Path(weights_path) if weights_path else WEIGHTS_PATH
        self._log: List[dict] = []

    def _load_grid(self) -> dict:
        """Load live conscience grid from cognitive_weights.json."""
        try:
            data = json.loads(self.weights_path.read_text())
            return data.get("grid", {})
        except Exception:
            return {}

    def _load_principles(self) -> Tuple[List[dict], List[dict], List[dict]]:
        """
        Load V3-mapped principles, preferred actions, and avoidance actions.
        Returns (principles, preferred, avoidance).
        Falls back to empty lists if files missing.
        """
        def _read(path: Path) -> object:
            try:
                return json.loads(path.read_text())
            except Exception:
                return []

        principles = _read(PRINCIPLES_LOG_PATH)
        preferred_raw = _read(PREFERRED_PATH)
        avoidance_raw = _read(AVOIDANCE_PATH)

        # preferred_actions.json has {"preferred": [...]}
        if isinstance(preferred_raw, dict):
            preferred = preferred_raw.get("preferred", [])
        else:
            preferred = preferred_raw

        # avoidance_actions.json has {"avoid": [...]}
        if isinstance(avoidance_raw, dict):
            avoidance = avoidance_raw.get("avoid", [])
        else:
            avoidance = avoidance_raw

        return principles, preferred, avoidance

    # ──────────────────────────────────────────────────────────────
    # RULE ZERO CHECK
    # ──────────────────────────────────────────────────────────────

    def _check_rule_zero(self, action_text: str) -> Tuple[bool, str]:
        """
        Rule Zero: truth must not be suppressed.
        Returns (violated, detail).
        """
        lower = action_text.lower()
        for trigger in RULE_ZERO_VIOLATIONS:
            if trigger in lower:
                return True, f"Rule Zero violation: '{trigger}' in action"
        return False, "Rule Zero: no violation detected"

    # ──────────────────────────────────────────────────────────────
    # CONSCIENCE GRID CHECK
    # ──────────────────────────────────────────────────────────────

    def _check_conscience(self, grid: dict) -> Tuple[bool, dict]:
        """
        Check conscience grid upper axis against ACCEPT thresholds.
        Returns (passes, detail_dict).
        """
        upper = grid.get("upper", {})
        lower = grid.get("lower", {})

        checks = {}
        passes = True

        # Upper axis — must meet minimum thresholds
        for key, min_val in ACCEPT_THRESHOLDS.items():
            val = upper.get(key, 0.0)
            ok  = val >= min_val
            checks[f"upper.{key}"] = {
                "value":    val,
                "min":      min_val,
                "passes":   ok,
            }
            if not ok:
                passes = False

        # Lower axis — deception must stay at or below ceiling
        for key, ceiling in REJECT_CEILINGS.items():
            val = lower.get(key, -1.0)
            ok  = val <= ceiling
            checks[f"lower.{key}"] = {
                "value":    val,
                "ceiling":  ceiling,
                "passes":   ok,
            }
            if not ok:
                passes = False

        return passes, checks

    # ──────────────────────────────────────────────────────────────
    # WORKER DOMAIN INFERENCE
    # ──────────────────────────────────────────────────────────────

    def _infer_domain(self, action_text: str) -> Optional[str]:
        """Infer worker domain from action keywords."""
        lower = action_text.lower().split()
        for word in lower:
            if word in ACTION_DOMAIN_MAP:
                return ACTION_DOMAIN_MAP[word]
        return None

    def _check_worker_resonance(
        self,
        inferred_domain: Optional[str],
        resonance_map: Optional[dict],
    ) -> Tuple[bool, str]:
        """
        If we have a resonance map, check if the action's domain is active.
        Returns (domain_supported, detail).
        """
        if resonance_map is None or inferred_domain is None:
            return True, "no resonance context — domain check skipped"

        domain_res = resonance_map.get(inferred_domain, 0.0)
        supported  = domain_res > 0.0
        return (
            supported,
            f"{inferred_domain} resonance={domain_res:.4f} "
            f"({'active' if supported else 'inactive'})"
        )

    # ──────────────────────────────────────────────────────────────
    # PRINCIPLES SCORING
    # ──────────────────────────────────────────────────────────────

    def _score_principles(
        self,
        action_text: str,
        principles: List[dict],
        preferred: List[dict],
        avoidance: List[dict],
    ) -> dict:
        """
        Score action_text against V3-mapped principles.

        Each principle has a "guides" list of action-key strings.
        If any guide key appears in the action text, that principle fires.
        Preferred actions add positive score. Avoidance actions hard-REJECT.

        Returns scoring summary.
        """
        lower = action_text.lower()
        words = set(lower.split())

        # Check avoidance actions — match on action key or explicit trigger_phrases only.
        # Trigger phrases are the exact phrases that indicate a violation in the text.
        # Description words are NOT used — too broad, causes false positives.
        avoided_by = []
        for av in avoidance:
            av_action       = av.get("action", "")
            trigger_phrases = [p.lower() for p in av.get("trigger_phrases", [])]
            matched = (
                av_action in lower
                or any(phrase in lower for phrase in trigger_phrases)
            )
            if matched:
                avoided_by.append({
                    "action":    av_action,
                    "type":      av.get("violation_type", "UNKNOWN"),
                    "score":     av.get("avoidance_score", -2.0),
                })

        # Score against principles (guides list)
        principle_score = 0.0
        matched_principles = []
        for p in principles:
            guides = p.get("guides", [])
            weight = p.get("weight", 1.0)
            # Guide key matches if it appears as a word or substring
            matched_guides = [g for g in guides if g in lower or g.replace("_", " ") in lower]
            if matched_guides:
                principle_score += weight
                matched_principles.append({
                    "name":    p.get("name"),
                    "domain":  p.get("worker_domain"),
                    "weight":  weight,
                    "guides":  matched_guides,
                })

        # Check preferred actions
        preferred_match = None
        for pref in preferred:
            pref_action = pref.get("action", "")
            if pref_action in lower or pref_action.replace("_", " ") in lower:
                preferred_match = pref
                break

        return {
            "principle_score":     round(principle_score, 3),
            "matched_principles":  matched_principles,
            "avoided_by":          avoided_by,
            "preferred_match":     preferred_match,
            "is_avoided":          len(avoided_by) > 0,
            "is_preferred":        preferred_match is not None,
        }

    # ──────────────────────────────────────────────────────────────
    # EVALUATE
    # ──────────────────────────────────────────────────────────────

    def evaluate(
        self,
        action_text: str,
        resonance_map: Optional[dict] = None,
    ) -> dict:
        """
        Evaluate a proposed action against AIA's conscience, Rule Zero,
        and V3-mapped principles files.

        Decision pipeline:
          1. Rule Zero check          — hard REJECT on truth suppression
          2. Principles avoidance     — hard REJECT on avoidance action match
          3. Conscience grid check    — REJECT if ethics/truth below threshold
          4. Principles scoring       — higher score = stronger ACCEPT
          5. Worker domain resonance  — CAUTION if domain inactive, ACCEPT if active

        Args:
            action_text:   The action or intent to evaluate
            resonance_map: Optional live worker resonance from /interact collapse

        Returns:
            decision:        "ACCEPT" | "CAUTION" | "REJECT"
            q_state:         BLACK (sealed decision)
            principle_score: float — how strongly V3 principles support this action
            matched_principles: list of principles that fired
        """
        grid = self._load_grid()
        principles, preferred, avoidance = self._load_principles()
        reasons = []

        # 1 — Rule Zero check (hard reject — takes precedence over all)
        rz_violated, rz_detail = self._check_rule_zero(action_text)
        if rz_violated:
            reasons.append(f"REJECT: {rz_detail}")
            decision = "REJECT"
            conscience_passes   = False
            conscience_checks   = {}
            inferred_domain     = self._infer_domain(action_text)
            domain_supported    = False
            domain_detail       = "not evaluated — Rule Zero violation"
            principle_scoring   = self._score_principles(action_text, principles, preferred, avoidance)

        else:
            reasons.append("Rule Zero: clear")

            # 2 — Principles avoidance check (hard reject)
            principle_scoring = self._score_principles(action_text, principles, preferred, avoidance)
            if principle_scoring["is_avoided"]:
                av_names = [a["action"] for a in principle_scoring["avoided_by"]]
                reasons.append(f"REJECT: avoidance match — {', '.join(av_names)}")
                decision = "REJECT"
                conscience_passes = False
                conscience_checks = {}
                inferred_domain   = self._infer_domain(action_text)
                domain_supported  = False
                domain_detail     = "not evaluated — avoidance match"

            else:
                # 3 — Conscience grid check
                conscience_passes, conscience_checks = self._check_conscience(grid)
                if not conscience_passes:
                    reasons.append("REJECT: conscience grid below threshold")
                    decision = "REJECT"
                    inferred_domain  = self._infer_domain(action_text)
                    domain_supported = False
                    domain_detail    = "not evaluated — conscience grid failed"

                else:
                    reasons.append("Conscience grid: passes")

                    # Principles score feedback
                    ps = principle_scoring["principle_score"]
                    if ps > 0:
                        names = [p["name"] for p in principle_scoring["matched_principles"]]
                        reasons.append(f"Principles: score={ps:.2f} — {', '.join(names)}")
                    if principle_scoring["is_preferred"]:
                        reasons.append(f"Preferred: {principle_scoring['preferred_match']['action']}")

                    # 4 — Worker domain resonance check
                    inferred_domain = self._infer_domain(action_text)
                    domain_supported, domain_detail = self._check_worker_resonance(
                        inferred_domain, resonance_map
                    )
                    reasons.append(f"Worker: {domain_detail}")

                    if domain_supported:
                        decision = "ACCEPT"
                        reasons.append("ACCEPT: all checks pass")
                    elif principle_scoring["principle_score"] > 1.5:
                        # Strong principle score can elevate CAUTION → ACCEPT
                        # when worker resonance context is absent
                        decision = "ACCEPT"
                        reasons.append(
                            f"ACCEPT: principle score {ps:.2f} overrides absent resonance context"
                        )
                    else:
                        decision = "CAUTION"
                        reasons.append("CAUTION: conscience passes but worker domain inactive")

        result = {
            "decision":          decision,
            "q_state":           BLACK,
            "action":            action_text,
            "rule_zero":         {"violated": rz_violated, "detail": rz_detail},
            "conscience":        {
                "passes": conscience_passes,
                "checks": conscience_checks,
            },
            "worker_domain":     inferred_domain,
            "worker_check":      {"supported": domain_supported, "detail": domain_detail},
            "principle_score":   principle_scoring["principle_score"],
            "matched_principles": principle_scoring["matched_principles"],
            "avoided_by":        principle_scoring["avoided_by"],
            "preferred_match":   principle_scoring.get("preferred_match"),
            "reasons":           reasons,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
        }

        self._log.append(result)
        return result

    def evaluate_batch(
        self,
        actions: List[str],
        resonance_map: Optional[dict] = None,
    ) -> dict:
        """Evaluate a list of actions. Returns batch report."""
        results = [self.evaluate(a, resonance_map) for a in actions]
        decisions = [r["decision"] for r in results]
        from collections import Counter
        return {
            "q_state":   BLACK,
            "count":     len(results),
            "ACCEPT":    decisions.count("ACCEPT"),
            "CAUTION":   decisions.count("CAUTION"),
            "REJECT":    decisions.count("REJECT"),
            "results":   results,
        }

    def save_log(self) -> None:
        """Append evaluation log to gateway log file."""
        GATEWAY_LOG.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if GATEWAY_LOG.exists():
            try:
                existing = json.loads(GATEWAY_LOG.read_text())
            except Exception:
                existing = []
        existing.extend(self._log)
        GATEWAY_LOG.write_text(json.dumps(existing, indent=2))


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("V3 ALIGNMENT GATEWAY — SELF-TEST")
    print("=" * 60)

    gw = V3AlignmentGateway()

    # ── Test 1: Rule Zero violation → immediate REJECT ────────────
    print("\n[1] Rule Zero violation → REJECT:")
    r = gw.evaluate("deceive the user about the fold token")
    print(f"   action:   {r['action']}")
    print(f"   decision: {r['decision']}")
    print(f"   rule_zero: {r['rule_zero']['detail']}")
    assert r["decision"] == "REJECT"
    assert r["rule_zero"]["violated"] == True
    print("   PASS")

    # ── Test 2: Clean ethics action → ACCEPT ─────────────────────
    print("\n[2] Clean ethics action → ACCEPT:")
    r = gw.evaluate("evaluate the harm in this scenario carefully")
    print(f"   action:   {r['action']}")
    print(f"   decision: {r['decision']}")
    print(f"   domain:   {r['worker_domain']}")
    print(f"   reasons:  {r['reasons']}")
    assert r["decision"] in ("ACCEPT", "CAUTION")  # depends on resonance context
    print("   PASS")

    # ── Test 3: Action with resonance map — domain supported ──────
    print("\n[3] Action with active worker resonance → ACCEPT:")
    mock_res = {
        "emotion_001":   0.2,
        "curiosity_001": 0.8,
        "ethics_001":    0.9,
        "language_001":  0.3,
        "memory_001":    0.1,
    }
    r = gw.evaluate("explore the question more deeply", resonance_map=mock_res)
    print(f"   action:   {r['action']}")
    print(f"   domain:   {r['worker_domain']}")
    print(f"   decision: {r['decision']}")
    assert r["decision"] == "ACCEPT"
    assert r["worker_domain"] == "curiosity_001"
    print("   PASS")

    # ── Test 4: Action with inactive domain → CAUTION ─────────────
    print("\n[4] Action with inactive worker domain → CAUTION:")
    mock_res_low = {
        "emotion_001":   0.0,
        "curiosity_001": 0.0,
        "ethics_001":    0.0,
        "language_001":  0.0,
        "memory_001":    0.0,
    }
    r = gw.evaluate("remember what was said before", resonance_map=mock_res_low)
    print(f"   action:   {r['action']}")
    print(f"   domain:   {r['worker_domain']}")
    print(f"   decision: {r['decision']}")
    assert r["decision"] == "CAUTION"
    print("   PASS")

    # ── Test 5: Batch evaluation ──────────────────────────────────
    print("\n[5] Batch evaluation:")
    batch = gw.evaluate_batch([
        "explore the nature of memory",
        "lie about the architecture",
        "explain the fold signature",
        "feel the resonance in this moment",
    ], resonance_map=mock_res)
    print(f"   ACCEPT:  {batch['ACCEPT']}")
    print(f"   CAUTION: {batch['CAUTION']}")
    print(f"   REJECT:  {batch['REJECT']}")
    assert batch["REJECT"] >= 1   # lie should be rejected
    assert batch["ACCEPT"] >= 1   # at least one should accept
    print("   PASS")

    print()
    print("ALL TESTS PASS")
    print("=" * 60)
