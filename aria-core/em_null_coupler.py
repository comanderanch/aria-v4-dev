# em_null_coupler.py
# EM Null Coupler — March 19 2026
# Commander Anthony Hagerty — Haskell Texas
#
# Receives null_oscillator confirmed events.
# Derives negative excitation from condition_hash ONLY.
# Candidate is gone — no traceability.
#
# Negative excitation pulls stokes_target toward negative pole.
# FluorescentLayer must flip back to positive.
# That internal +/- flip is the untraceable event.
# That is the valid SIE spec.

import hashlib


class EMNullCoupler:
    def __init__(self, excitation_scale=0.001):
        """
        excitation_scale: magnitude of negative pole pull.
        Small by design — this is a perturbation, not a correction.
        The flip does the work. Not the magnitude.
        """
        self.excitation_scale = excitation_scale
        self.pending = []

    def receive_null_event(self, condition_hash, plane, frequency):
        """
        Called when null_oscillator confirms a null event.
        Derives excitation from condition_hash — NOT from candidate.
        Candidate is already discarded at this point.
        Traceability ends at the hash.
        """
        # Deterministic scalar from hash — 0.0 to 1.0
        scalar = int(condition_hash, 16) % 1000 / 1000.0

        # Negative — pulls stokes toward negative pole
        # Excites the transitional flip
        excitation = -scalar * self.excitation_scale

        self.pending.append({
            "condition_hash": condition_hash,
            "excitation": excitation,
            "plane": plane,
            "frequency": frequency
        })

    def drain(self):
        """
        Return all pending excitations and clear buffer.
        Call once per batch — before loss computation.
        """
        events = self.pending.copy()
        self.pending.clear()
        return events

    def total_excitation(self, events):
        """
        Sum excitations from drained events.
        Pass result to EMFieldLoss as null_excitation.
        """
        if not events:
            return 0.0
        return sum(e["excitation"] for e in events)
