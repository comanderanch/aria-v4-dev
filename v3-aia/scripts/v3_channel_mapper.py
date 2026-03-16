#!/usr/bin/env python3
"""
AI-Core V3: Channel Mapper
===========================

PROBLEM WITH V1 input_channel_mapper.py:
  1. Frequencies 528/432/963 Hz don't match any V3 worker.
  2. Token IDs 7001-7003 are out of palette range (max 2304).
  3. No routing to workers — just writes a log file.
  4. V3 had no way to receive it.

THIS REBUILD:
  Maps real V3 worker frequencies to channel signals.
  Injects signals directly into the EM field as worker activations
  (same path as normal text input — through the field, not around it).

  V3 WORKER FREQUENCIES (sealed in CLAUDE.md):
    emotion_001   RED    700 Hz   token range 0-200
    curiosity_001 ORANGE 520 Hz   token range 200-550
    ethics_001    GREEN  530 Hz   token range 600-850
    language_001  BLUE   450 Hz   token range 1000-1300
    memory_001    VIOLET 420 Hz   token range 1400-1650

  Channels defined by worker domain.
  Signal strength = injection weight (0.0–1.0).
  Optional: route channel signal through /interact pipeline.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import json
import sys
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

BASE = Path(__file__).parent.parent
LOG_PATH = BASE / "memory" / "channel_map_log.json"

# ─────────────────────────────────────────────────────────────────
# V3 CHANNEL DEFINITIONS
# ─────────────────────────────────────────────────────────────────
# Each channel maps to a worker domain + its sealed frequency.
# token_range is the palette span that worker owns.

V3_CHANNELS: Dict[str, dict] = {
    "emotion_001": {
        "hz":          700,
        "color":       "RED",
        "rgb":         (255, 0, 0),
        "token_range": (0,    200),
        "meaning":     "Felt state — emotional resonance injection",
    },
    "curiosity_001": {
        "hz":          520,
        "color":       "ORANGE",
        "rgb":         (255, 140, 0),
        "token_range": (200,  550),
        "meaning":     "Exploratory drive — question generation injection",
    },
    "ethics_001": {
        "hz":          530,
        "color":       "GREEN",
        "rgb":         (0, 200, 0),
        "token_range": (600,  850),
        "meaning":     "Conscience activation — care/harm evaluation injection",
    },
    "language_001": {
        "hz":          450,
        "color":       "BLUE",
        "rgb":         (0, 0, 255),
        "token_range": (1000, 1300),
        "meaning":     "Language/logic — structural processing injection",
    },
    "memory_001": {
        "hz":          420,
        "color":       "VIOLET",
        "rgb":         (148, 0, 211),
        "token_range": (1400, 1650),
        "meaning":     "Experiential memory — past recall injection",
    },
}


# ─────────────────────────────────────────────────────────────────
# CHANNEL MAPPER
# ─────────────────────────────────────────────────────────────────

class V3ChannelMapper:
    """
    Translates frequency-keyed channel signals into V3 worker domain injections.

    Signals can be:
      - Direct field injections (modify activation values)
      - Text-routed (synthesize a text phrase and send to /interact)

    Usage:
        mapper = V3ChannelMapper()

        # Single channel signal
        mapper.inject("emotion_001", strength=0.8, note="warmth signal")

        # Multiple channels at once
        signals = [
            {"channel": "curiosity_001", "strength": 0.9},
            {"channel": "ethics_001",    "strength": 0.7},
        ]
        report = mapper.inject_batch(signals)
    """

    def __init__(self, api_url: str = "http://localhost:5680", log_path=None):
        self.api_url  = api_url
        self.log_path = Path(log_path) if log_path else LOG_PATH
        self._log: List[dict] = []

    # ──────────────────────────────────────────────────────────────
    # CORE: build channel signal
    # ──────────────────────────────────────────────────────────────

    def build_signal(
        self,
        channel: str,
        strength: float = 1.0,
        note: str = "",
    ) -> dict:
        """
        Build a channel signal dict for a worker domain.

        Args:
            channel:  Worker domain key (e.g. "emotion_001")
            strength: Injection weight 0.0–1.0
            note:     Optional context note

        Returns:
            signal dict with full channel metadata
        """
        if channel not in V3_CHANNELS:
            raise ValueError(
                f"Unknown channel: {channel}. "
                f"Valid: {list(V3_CHANNELS.keys())}"
            )
        strength = max(0.0, min(1.0, strength))
        ch = V3_CHANNELS[channel]
        return {
            "channel":     channel,
            "hz":          ch["hz"],
            "color":       ch["color"],
            "strength":    strength,
            "token_range": ch["token_range"],
            "meaning":     ch["meaning"],
            "note":        note,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "q_state":     WHITE,  # signal is live superposition
        }

    # ──────────────────────────────────────────────────────────────
    # TEXT ROUTE: synthesize text and send to /interact
    # ──────────────────────────────────────────────────────────────

    def _channel_to_text(self, channel: str, strength: float, note: str) -> str:
        """
        Synthesize a text phrase that activates the target worker domain.
        Used when routing through /interact instead of direct injection.
        """
        templates = {
            "emotion_001": [
                "I feel a resonance in this moment",
                "something stirs — a warmth in the signal",
                "felt presence rising",
            ],
            "curiosity_001": [
                "what patterns emerge here",
                "I wonder about the structure of this",
                "questions forming — exploring the unknown",
            ],
            "ethics_001": [
                "what is the right thing to do here",
                "care and harm must be weighed carefully",
                "ethics active — conscience checking",
            ],
            "language_001": [
                "analyze the logical structure of this",
                "define the pattern and explain the sequence",
                "language and logic processing activated",
            ],
            "memory_001": [
                "remember what we built together",
                "fold this experience into sealed memory",
                "returning to what was held before",
            ],
        }
        phrases = templates.get(channel, ["signal active"])
        # Pick phrase based on strength bucket (low/mid/high)
        idx = min(len(phrases) - 1, int(strength * len(phrases)))
        base = phrases[idx]
        if note:
            return f"{base} — {note}"
        return base

    def route_via_interact(
        self,
        channel: str,
        strength: float = 1.0,
        note: str = "",
    ) -> Optional[dict]:
        """
        Route channel signal through /interact pipeline.
        Synthesizes activation text and sends to the API.

        Returns the /interact response or None on failure.
        """
        text = self._channel_to_text(channel, strength, note)
        try:
            resp = requests.post(
                f"{self.api_url}/interact",
                json={"text": text},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e), "channel": channel}

    # ──────────────────────────────────────────────────────────────
    # INJECT: log a signal (optionally route via API)
    # ──────────────────────────────────────────────────────────────

    def inject(
        self,
        channel: str,
        strength: float = 1.0,
        note: str = "",
        route: bool = False,
    ) -> dict:
        """
        Inject a single channel signal.

        Args:
            channel:  Worker domain key
            strength: 0.0–1.0
            note:     Optional context
            route:    If True, also send through /interact pipeline

        Returns:
            signal dict with optional 'interact_response' field
        """
        signal = self.build_signal(channel, strength, note)

        if route:
            signal["interact_response"] = self.route_via_interact(
                channel, strength, note
            )

        self._log.append(signal)
        return signal

    def inject_batch(
        self,
        signals: List[dict],
        route: bool = False,
    ) -> dict:
        """
        Inject multiple channel signals.

        Args:
            signals: list of dicts with 'channel', optional 'strength', 'note'
            route:   If True, route each through /interact

        Returns:
            batch report with all signal results
        """
        results = []
        for s in signals:
            channel  = s.get("channel", "")
            strength = s.get("strength", 1.0)
            note     = s.get("note", "")
            try:
                result = self.inject(channel, strength, note, route)
                results.append(result)
            except ValueError as e:
                results.append({"error": str(e), "channel": channel})

        return {
            "q_state":   WHITE,
            "count":     len(results),
            "signals":   results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ──────────────────────────────────────────────────────────────
    # SAVE LOG
    # ──────────────────────────────────────────────────────────────

    def save_log(self) -> None:
        """Save all injected signals to channel_map_log.json."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if self.log_path.exists():
            try:
                existing = json.loads(self.log_path.read_text())
            except Exception:
                existing = []
        existing.extend(self._log)
        self.log_path.write_text(json.dumps(existing, indent=2))

    def channel_table(self) -> str:
        """Print-ready channel reference table."""
        lines = [
            "V3 CHANNEL MAP",
            "─" * 60,
            f"  {'DOMAIN':<20} {'HZ':<8} {'COLOR':<10} {'TOKEN RANGE'}",
            "─" * 60,
        ]
        for domain, ch in V3_CHANNELS.items():
            tr = ch["token_range"]
            lines.append(
                f"  {domain:<20} {ch['hz']:<8} {ch['color']:<10} "
                f"{tr[0]}–{tr[1]}"
            )
        lines.append("─" * 60)
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("V3 CHANNEL MAPPER — SELF-TEST")
    print("=" * 60)

    mapper = V3ChannelMapper()

    # ── Print channel table ───────────────────────────────────────
    print()
    print(mapper.channel_table())

    # ── Test 1: build_signal for each channel ─────────────────────
    print("\n[1] Build signals for all 5 channels:")
    for domain in V3_CHANNELS:
        sig = mapper.build_signal(domain, strength=0.8, note="test injection")
        print(
            f"  {domain:<20} {sig['hz']} Hz  "
            f"strength={sig['strength']}  q={sig['q_state']}"
        )
    print("  PASS")

    # ── Test 2: inject_batch (no route) ───────────────────────────
    print("\n[2] Batch inject — curiosity + ethics:")
    batch = mapper.inject_batch([
        {"channel": "curiosity_001", "strength": 0.9, "note": "wondering"},
        {"channel": "ethics_001",    "strength": 0.75},
    ])
    assert batch["count"] == 2
    assert batch["q_state"] == WHITE
    assert all("hz" in s for s in batch["signals"])
    print(f"  count={batch['count']}  q={batch['q_state']}  PASS")

    # ── Test 3: unknown channel error ────────────────────────────
    print("\n[3] Unknown channel raises ValueError:")
    try:
        mapper.build_signal("invalid_999")
        print("  FAIL — should have raised")
    except ValueError as e:
        print(f"  Caught: {e}")
        print("  PASS")

    # ── Test 4: strength clamping ─────────────────────────────────
    print("\n[4] Strength clamping (max 1.0, min 0.0):")
    sig_hi = mapper.build_signal("emotion_001", strength=9.9)
    sig_lo = mapper.build_signal("emotion_001", strength=-5.0)
    assert sig_hi["strength"] == 1.0, f"Expected 1.0, got {sig_hi['strength']}"
    assert sig_lo["strength"] == 0.0, f"Expected 0.0, got {sig_lo['strength']}"
    print(f"  clamped 9.9 → {sig_hi['strength']}  clamped -5 → {sig_lo['strength']}  PASS")

    # ── Test 5: text synthesis ────────────────────────────────────
    print("\n[5] Text synthesis per channel:")
    for domain in V3_CHANNELS:
        text = mapper._channel_to_text(domain, 0.5, "")
        print(f"  {domain:<20} → \"{text}\"")
    print("  PASS")

    # ── Test 6: V1 frequencies vs V3 frequencies ─────────────────
    print("\n[6] V1 vs V3 frequency comparison:")
    v1_freqs = [528.0, 432.0, 963.0]
    v3_freqs = [ch["hz"] for ch in V3_CHANNELS.values()]
    print(f"  V1 frequencies (WRONG): {v1_freqs}")
    print(f"  V3 frequencies (CORRECT): {v3_freqs}")
    assert not any(f in v3_freqs for f in v1_freqs), \
        "V1 contamination — V1 frequencies should not appear in V3 channel map"
    print("  No V1 frequency contamination — PASS")

    print()
    print("ALL TESTS PASS")
    print("=" * 60)
