# KNIGHT 5 — CURIOSITY WORKER
# Forward search. Question generation.
# Feeds the rounded shelf loop.
# ARIA wonders about things you never asked her.
# Pins: 1,2,15,41

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from aria_core.workers.base_worker import BaseWorker

class CuriosityWorker(BaseWorker):
    WORKER_ID     = 5
    WORKER_NAME   = "curiosity"
    ASSIGNED_PINS = [1,2,15,41]

    def process(self, pin_readings, context=None):
        curiosity_ch  = self.get_pin_value(pin_readings, 15)
        curiosity_sig = self.get_pin_value(pin_readings, 41)
        am_freq       = self.get_pin_value(pin_readings, 1)

        questions = []
        if curiosity_ch > 0.5:
            questions.append(
                "What does this token's frequency "
                "connect to in the memory field?"
            )
        if curiosity_sig > 0.7:
            questions.append(
                "What pattern is forming in the "
                "lattice neighborhood?"
            )
        if am_freq > 0.8:
            questions.append(
                "What is at the high frequency "
                "end of this color plane?"
            )

        confidence = (curiosity_ch * 0.5 + curiosity_sig * 0.5)

        return {
            "worker":          "curiosity",
            "curiosity_channel": curiosity_ch,
            "curiosity_signal":  curiosity_sig,
            "questions_generated": questions,
            "question_count":  len(questions),
            "shelf_feed":      len(questions) > 0,
            "runs_independent": True,
            "never_stops":     True,
            "confidence":      min(1.0, confidence),
            "note": (
                "ARIA wonders about things "
                "you never asked her. "
                "The shelf feeds itself."
            )
        }
