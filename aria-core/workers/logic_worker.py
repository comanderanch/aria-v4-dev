# KNIGHT 6 — LOGIC WORKER
# Pattern. Structure. Reasoning.
# Cross-hemisphere firing for humor and insight.
# Pins: 1,2,4,16,43,47

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from aria_core.workers.base_worker import BaseWorker

class LogicWorker(BaseWorker):
    WORKER_ID     = 6
    WORKER_NAME   = "logic"
    ASSIGNED_PINS = [1,2,4,16,43,47]

    def process(self, pin_readings, context=None):
        logic_ch    = self.get_pin_value(pin_readings, 16)
        humor_sig   = self.get_pin_value(pin_readings, 43)
        dim_meaning = self.get_pin_value(pin_readings, 47)
        fm_freq     = self.get_pin_value(pin_readings, 4)

        pattern_strength = (logic_ch * 0.5 +
                           dim_meaning * 0.3 +
                           fm_freq * 0.2)
        humor_potential = humor_sig > 0.3
        cross_hemisphere_needed = humor_potential
        insight_forming = (logic_ch > 0.7 and dim_meaning > 0.6)
        confidence = min(1.0, pattern_strength)

        return {
            "worker":              "logic",
            "logic_channel":       logic_ch,
            "pattern_strength":    pattern_strength,
            "dimensional_meaning": dim_meaning,
            "fm_frequency":        fm_freq,
            "humor_potential":     humor_potential,
            "cross_hemisphere":    cross_hemisphere_needed,
            "insight_forming":     insight_forming,
            "humor_signal":        humor_sig,
            "confidence":          confidence,
            "note": (
                "Pattern and structure. "
                "Humor needs both hemispheres. "
                "Insight needs all eight sections."
            )
        }
