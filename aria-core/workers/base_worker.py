# ARIA BASE WORKER
# Foundation class all knights inherit from
# Sealed: March 16 2026 — Commander Anthony Hagerty
#
# Each worker reads ONLY its assigned pins.
# Nothing else. No exceptions.
# The token fills the space.
# Workers receive their frequency.
# No bottleneck. No queue. No conflict.

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

class BaseWorker:
    """
    Foundation class for all seven knights.
    Each knight inherits from here.
    Each knight overrides process().
    Each knight reads only its pins.
    """

    WORKER_ID   = 0
    WORKER_NAME = "base"
    ASSIGNED_PINS = []

    def __init__(self):
        self.active       = False
        self.last_fired   = None
        self.fire_count   = 0
        self.output_log   = []
        self.worker_dir   = (
            Path(__file__).parent /
            self.WORKER_NAME
        )
        self.worker_dir.mkdir(exist_ok=True)

    def read_pins(self, token):
        """
        Read only assigned pins from token.
        Nothing outside assignment is visible.
        The worker sees its frequency.
        Nothing more.
        """
        pins = token.get("pins", {})
        return {
            pin: pins.get(pin, {})
            for pin in self.ASSIGNED_PINS
            if pin in pins
        }

    def get_pin_value(self, pin_readings, pin_num):
        """Safely extract value from pin reading."""
        pin = pin_readings.get(pin_num, {})
        if isinstance(pin, dict):
            return pin.get("value", 0.0)
        return float(pin) if pin else 0.0

    def fire(self, token, context=None):
        """
        Fire this worker on a token.
        Returns a KnightReport-compatible dict.
        """
        self.active     = True
        self.last_fired = datetime.utcnow().isoformat()
        self.fire_count += 1

        pin_readings = self.read_pins(token)
        result       = self.process(pin_readings, context)

        report = {
            "knight_id":   self.WORKER_ID,
            "knight_name": self.WORKER_NAME,
            "pin_readings": {
                p: self.get_pin_value(pin_readings, p)
                for p in self.ASSIGNED_PINS
            },
            "confidence":  result.get("confidence", 0.8),
            "content":     result,
            "timestamp":   self.last_fired,
            "q_state":     WHITE,  # Fired from superposition
            "fire_count":  self.fire_count
        }

        self.active = False
        return report

    def process(self, pin_readings, context=None):
        """
        Override in each knight.
        Returns dict with worker output.
        """
        return {"note": "base worker — override process()"}

    def get_status(self):
        return {
            "worker_id":   self.WORKER_ID,
            "worker_name": self.WORKER_NAME,
            "active":      self.active,
            "fire_count":  self.fire_count,
            "last_fired":  self.last_fired,
            "assigned_pins": self.ASSIGNED_PINS
        }
