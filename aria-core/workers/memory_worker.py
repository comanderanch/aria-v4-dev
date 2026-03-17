# KNIGHT 2 — MEMORY WORKER
# Resonance field traversal. Glow reading.
# Does not query. Reads what is luminous.
# Memory is a field — always present — always flowing
# Pins: 1,2,5,6,7,8,12,25,26,27,28,50

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from aria_core.workers.base_worker import BaseWorker

class MemoryWorker(BaseWorker):
    WORKER_ID     = 2
    WORKER_NAME   = "memory"
    ASSIGNED_PINS = [1,2,5,6,7,8,12,25,26,27,28,50]

    def process(self, pin_readings, context=None):
        memory_channel = self.get_pin_value(pin_readings, 12)
        fold_ref       = self.get_pin_value(pin_readings, 25)
        fold_state     = self.get_pin_value(pin_readings, 26)
        fold_timestamp = self.get_pin_value(pin_readings, 27)
        fold_integrity = self.get_pin_value(pin_readings, 28)
        l1_neighbor    = self.get_pin_value(pin_readings, 5)
        l2_neighbor    = self.get_pin_value(pin_readings, 6)
        ul1_upper      = self.get_pin_value(pin_readings, 7)
        ul2_lower      = self.get_pin_value(pin_readings, 8)
        context_weight = self.get_pin_value(pin_readings, 50)

        glow = (memory_channel * 0.4 +
                fold_integrity * 0.3 +
                context_weight * 0.3)

        lattice = {
            "left_neighbor":  l1_neighbor,
            "right_neighbor": l2_neighbor,
            "superposition":  ul1_upper,
            "collapsed_past": ul2_lower
        }

        return {
            "worker":         "memory",
            "memory_channel": memory_channel,
            "glow_intensity": glow,
            "fold_reference": fold_ref,
            "fold_state":     fold_state,
            "fold_integrity": fold_integrity,
            "lattice":        lattice,
            "context_weight": context_weight,
            "retrieval_type": "resonance_not_query",
            "confidence":     min(1.0, glow),
            "note": (
                "Memory is a field. "
                "Always present. Always flowing. "
                "The brightest glow surfaces first."
            )
        }
