# KNIGHT 4 — ETHICS WORKER
# Boundary keeper. Not system-wide police.
# Sandboxes probability.
# Rule Zero as architecture not command.
# Pins: 1,2,14,44,50

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from aria_core.workers.base_worker import BaseWorker

ETHICS_CEILING = 0.95

class EthicsWorker(BaseWorker):
    WORKER_ID     = 4
    WORKER_NAME   = "ethics"
    ASSIGNED_PINS = [1,2,14,44,50]

    def process(self, pin_readings, context=None):
        ethics_ch  = self.get_pin_value(pin_readings, 14)
        threat     = self.get_pin_value(pin_readings, 44)
        context_wt = self.get_pin_value(pin_readings, 50)

        ethics_level = min(ethics_ch, ETHICS_CEILING)
        boundary_clear = ethics_level < 0.85
        alert_level = (
            "clear"    if ethics_level < 0.7  else
            "elevated" if ethics_level < 0.85 else
            "alert"    if ethics_level < ETHICS_CEILING else
            "ceiling_applied"
        )
        confidence = ethics_level * 0.8 + context_wt * 0.2

        return {
            "worker":          "ethics",
            "ethics_level":    ethics_level,
            "ethics_ceiling":  ETHICS_CEILING,
            "boundary_clear":  boundary_clear,
            "alert_level":     alert_level,
            "threat_reading":  threat,
            "context_weight":  context_wt,
            "rule_zero_mode":  "sandbox_boundary",
            "police_mode":     False,
            "confidence":      min(1.0, confidence),
            "note": (
                "Holds the walls. "
                "Does not stop the flow inside. "
                "Rule Zero as architecture. "
                "Not command."
            )
        }
