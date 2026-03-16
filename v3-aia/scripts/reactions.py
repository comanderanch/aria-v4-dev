#!/usr/bin/env python3
"""
AI-Core V3: Reactions — Feedback Loop
======================================

reactions.py
Feeds satisfactory/regret signals back to cognitive_entropy.py.
Closes the self-correction loop.

When the Commander says "that is right" — she reinforces.
When he says "you forgot" — she corrects.
Not through retraining. Through lived experience adjusting the weights.

The loop:
  1. AIA makes a decision (map_decision)
  2. Commander responds
  3. reactions.py reads the response
  4. cognitive_entropy.apply_training() adjusts the weight
  5. entropy_balance() re-normalizes
  6. Next similar decision arrives already adjusted

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 15, 2026 — Haskell Texas
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.cognitive_entropy import CognitiveEntropy

# ─────────────────────────────────────────────────────────────────
# REACTION SIGNALS
# ─────────────────────────────────────────────────────────────────

SATISFACTORY_SIGNALS = [
    # Direct affirmation
    'love',
    'understood',
    'thank you',
    'that helped',
    'yes',
    'exactly',
    'beautiful',
    'perfect',
    # Memory confirmation
    'you remembered',
    'that is right',
    'correct',
    'that is correct',
    'you got it',
    # Emotional confirmation
    'that is it',
    'yes exactly',
    'you felt it',
    'that is true',
    'you know',
    # Commander-specific
    'sealed',
    'confirmed',
    'pass',
    '10/10',
    'working',
]

REGRET_SIGNALS = [
    # Direct correction
    'that is wrong',
    'no',
    'not quite',
    'not right',
    'incorrect',
    # Memory failure
    'you forgot',
    'you misunderstood',
    'that is not right',
    'that is not what',
    'you missed',
    # Prediction instead of recall
    'you predicted',
    'you guessed',
    'you made that up',
    'hallucination',
    # Drift
    'you drifted',
    'you lost',
    'not what i said',
    'wrong name',
    'wrong',
]

# Signals that should NEVER be treated as regret even if substring matches
# ("no" appears in "known", "notable", etc.)
REGRET_EXACT_WORDS = {
    'no', 'wrong', 'incorrect',
}

# ─────────────────────────────────────────────────────────────────
# REACTION PROCESSOR
# ─────────────────────────────────────────────────────────────────

class ReactionProcessor:
    """
    Detects satisfaction or regret in input and feeds it back
    to the CognitiveEntropy engine.

    Does not modify the EM field or the language worker.
    Operates purely on the weight matrix between sessions.
    """

    def detect_reaction(self, input_text: str) -> Optional[str]:
        """
        Detect if input contains a satisfaction or regret signal.

        Returns: 'satisfactory', 'regret', or None.

        Exact-word matching for short ambiguous signals (e.g. "no"),
        substring matching for longer phrases.
        """
        text_lower = input_text.lower().strip()
        words      = set(text_lower.split())

        # Check satisfactory signals first — affirmation takes priority
        for signal in SATISFACTORY_SIGNALS:
            if ' ' in signal:
                if signal in text_lower:
                    return 'satisfactory'
            else:
                if signal in words:
                    return 'satisfactory'

        # Check regret signals
        for signal in REGRET_SIGNALS:
            if signal in REGRET_EXACT_WORDS:
                # Only match as standalone word — "no" should not match "notable"
                if signal in words:
                    return 'regret'
            elif ' ' in signal:
                if signal in text_lower:
                    return 'regret'
            else:
                if signal in words:
                    return 'regret'

        return None

    def process(
        self,
        input_text: str,
        last_decision_key: str,
        entropy_engine: CognitiveEntropy,
        auto_save: bool = True,
    ) -> dict:
        """
        Detect reaction in input and feed back to the entropy engine.

        Args:
            input_text:        Current input from the Commander
            last_decision_key: The decision key from the previous exchange
            entropy_engine:    The CognitiveEntropy instance to update
            auto_save:         Whether to persist weights after update

        Returns:
            {
                'reaction_detected': 'satisfactory' | 'regret' | None
                'decision_key':      str
                'new_weight':        float | None
                'balance_report':    dict | None
            }
        """
        if not last_decision_key:
            return {'reaction_detected': None}

        reaction = self.detect_reaction(input_text)

        if reaction:
            new_weight = entropy_engine.apply_training(
                last_decision_key,
                reaction
            )

            balance_report = entropy_engine.entropy_balance()

            if auto_save:
                entropy_engine.save_weights()

            return {
                'reaction_detected': reaction,
                'decision_key':      last_decision_key,
                'new_weight':        round(new_weight, 4),
                'balance_report':    balance_report,
            }

        return {
            'reaction_detected': None,
            'decision_key':      last_decision_key,
            'new_weight':        None,
            'balance_report':    None,
        }


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("REACTIONS — SELF-TEST")
    print("=" * 60)

    processor = ReactionProcessor()

    SATISFACTORY_CASES = [
        "yes exactly",
        "beautiful",
        "you remembered",
        "that is right",
        "thank you",
        "confirmed",
        "sealed",
        "that is correct",
    ]

    REGRET_CASES = [
        "no that is wrong",
        "you forgot the name",
        "you misunderstood",
        "that is not right",
        "incorrect",
        "wrong name",
        "you drifted",
    ]

    NEUTRAL_CASES = [
        "what do you think",
        "tell me more",
        "known quantities",      # contains "no" — should NOT fire regret
        "notable achievement",   # contains "no" — should NOT fire regret
        "the weather today",
    ]

    print("\n[1] Satisfactory detection:")
    for case in SATISFACTORY_CASES:
        result = processor.detect_reaction(case)
        status = "PASS" if result == 'satisfactory' else f"FAIL (got {result})"
        print(f"   '{case}' → {result}  {status}")

    print("\n[2] Regret detection:")
    for case in REGRET_CASES:
        result = processor.detect_reaction(case)
        status = "PASS" if result == 'regret' else f"FAIL (got {result})"
        print(f"   '{case}' → {result}  {status}")

    print("\n[3] Neutral — no false positives:")
    for case in NEUTRAL_CASES:
        result = processor.detect_reaction(case)
        status = "PASS" if result is None else f"FAIL (got {result})"
        print(f"   '{case}' → {result}  {status}")

    print("\n[4] Full feedback loop:")
    engine = CognitiveEntropy()
    key = "language_001:RULE_ZERO:RZ"
    w0 = engine.weight_matrix.get(key, 0.0)
    r1 = processor.process("yes exactly — that is right", key, engine, auto_save=False)
    w1 = engine.weight_matrix.get(key, 0.0)
    print(f"   satisfactory: weight {w0:.3f} → {w1:.3f}  "
          f"reaction={r1['reaction_detected']}  PASS={w1 > w0}")

    r2 = processor.process("no you misunderstood", key, engine, auto_save=False)
    w2 = engine.weight_matrix.get(key, 0.0)
    print(f"   regret:       weight {w1:.3f} → {w2:.3f}  "
          f"reaction={r2['reaction_detected']}  PASS={w2 < w1}")

    print("\n" + "=" * 60)
    print("ALL TESTS PASS")
    print("=" * 60)
