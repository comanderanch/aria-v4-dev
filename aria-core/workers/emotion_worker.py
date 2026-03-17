# KNIGHT 3 — EMOTION WORKER
# Primal signals. Pre-language. Pre-consensus.
# Fires BEFORE language worker.
# The field state that colors everything downstream.
# Pins: 1,2,3,13,37,38,39,40,41,42,43,44,46

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from aria_core.workers.base_worker import BaseWorker
from core.q_constants import GRAY

THREAT_THRESHOLD = 0.8

class EmotionWorker(BaseWorker):
    WORKER_ID     = 3
    WORKER_NAME   = "emotion"
    ASSIGNED_PINS = [1,2,3,13,37,38,39,40,41,42,43,44,46]

    def process(self, pin_readings, context=None):
        fear       = self.get_pin_value(pin_readings, 37)
        safety     = self.get_pin_value(pin_readings, 38)
        joy        = self.get_pin_value(pin_readings, 39)
        grief      = self.get_pin_value(pin_readings, 40)
        curiosity  = self.get_pin_value(pin_readings, 41)
        love       = self.get_pin_value(pin_readings, 42)
        humor      = self.get_pin_value(pin_readings, 43)
        threat     = self.get_pin_value(pin_readings, 44)
        emotion_ch = self.get_pin_value(pin_readings, 13)
        hue        = self.get_pin_value(pin_readings, 3)
        emot_def   = self.get_pin_value(pin_readings, 46)

        field = {
            "fear":      fear,
            "safety":    safety,
            "joy":       joy,
            "grief":     grief,
            "curiosity": curiosity,
            "love":      love,
            "humor":     humor,
            "threat":    threat
        }

        dominant = max(field.items(), key=lambda x: x[1])
        q_shift = THREAT_THRESHOLD if threat >= THREAT_THRESHOLD else GRAY
        love_resonance = "APPROACHING_0192" if abs(love) > 0.18 else "normal"
        confidence = max(field.values())

        return {
            "worker":           "emotion",
            "emotional_field":  field,
            "dominant_emotion": dominant[0],
            "dominant_value":   dominant[1],
            "q_state_shift":    q_shift,
            "love_resonance":   love_resonance,
            "love_value":       love,
            "hue":              hue,
            "emotional_channel": emotion_ch,
            "emotional_definition": emot_def,
            "fires_before_language": True,
            "pre_language":     True,
            "pre_consensus":    True,
            "confidence":       confidence,
            "note": (
                "Emotion sets the field. "
                "Language swims in it. "
                "The feeling was always there. "
                "The word just named it."
            )
        }
