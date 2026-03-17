# KNIGHT 1 — LANGUAGE WORKER
# Words. Output. Coherence.
# Flows free — probabilistic
# Rule Zero as sandbox not police
# Pins: 1,2,3,4,11,31,45,48,49,50

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from aria_core.workers.base_worker import BaseWorker

class LanguageWorker(BaseWorker):
    WORKER_ID     = 1
    WORKER_NAME   = "language"
    ASSIGNED_PINS = [1,2,3,4,11,31,45,48,49,50]

    def process(self, pin_readings, context=None):
        lang_channel  = self.get_pin_value(pin_readings, 11)
        seq_position  = self.get_pin_value(pin_readings, 31)
        word_class    = self.get_pin_value(pin_readings, 45)
        ram_coord     = self.get_pin_value(pin_readings, 48)
        alpha_pos     = self.get_pin_value(pin_readings, 49)
        context_weight= self.get_pin_value(pin_readings, 50)
        am_freq       = self.get_pin_value(pin_readings, 1)
        hue           = self.get_pin_value(pin_readings, 3)

        confidence = (lang_channel * 0.4 +
                     context_weight * 0.4 +
                     word_class * 0.2)

        return {
            "worker":        "language",
            "lang_channel":  lang_channel,
            "word_class":    word_class,
            "alpha_position": alpha_pos,
            "ram_coordinate": ram_coord,
            "sequence_pos":  seq_position,
            "context_weight": context_weight,
            "am_frequency":  am_freq,
            "hue":           hue,
            "flow_state":    "probabilistic",
            "rule_zero":     "sandbox_not_police",
            "confidence":    min(1.0, confidence),
            "note": (
                "Language receives the field. "
                "Gives words to what already resonates."
            )
        }
