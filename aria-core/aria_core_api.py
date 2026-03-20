#!/usr/bin/env python3
"""
ARIA — CORE REST API
====================
Session 5 — Unification Layer — March 20 2026
Commander Anthony Hagerty — Haskell Texas
Sealed by: CLI Claude (Sonnet 4.6)

Thin Flask wrapper around aria_core_think().
One endpoint. One function. One mind.

ENDPOINT:
  POST /think   — everything enters here
  GET  /health  — is she alive
  GET  /state   — model state

PORT: 5750

This file does NOT contain logic.
All logic lives in aria_core_think().
This file is just the door.

NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import logging
from pathlib import Path
from flask import Flask, request, jsonify

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from aria_core.aria_core_think import aria_core_think, load_model, \
    _checkpoint_name, _best_loss, _tokenizer, DEVICE

# ── LOGGING ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  ARIA-API  %(message)s")
log = logging.getLogger("aria.api")

PORT = 5750

# ── APP ─────────────────────────────────────────────────────────────────────────
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    from aria_core.aria_core_think import _checkpoint_name, _best_loss, _tokenizer
    return jsonify({
        "status":    "alive",
        "model":     _checkpoint_name,
        "loss":      round(_best_loss, 6),
        "vocab":     len(_tokenizer.vocab) if _tokenizer else 0,
        "device":    str(DEVICE),
    })


@app.route("/state", methods=["GET"])
def state():
    from aria_core.aria_core_think import _checkpoint_name, _best_loss, _tokenizer
    return jsonify({
        "checkpoint":  _checkpoint_name,
        "loss":        round(_best_loss, 6),
        "vocab_size":  len(_tokenizer.vocab) if _tokenizer else 0,
        "device":      str(DEVICE),
        "attractor":   0.192,
        "q_state":     "GRAY=0",
        "core_route":  "aria_core_think()",
    })


@app.route("/think", methods=["POST"])
def think():
    """
    The one endpoint.
    Routes to aria_core_think() — the one function.
    Nothing else.
    """
    data = request.get_json(silent=True) or {}

    # Accept "input" or "prompt" for compatibility
    input_text = data.get("input") or data.get("prompt") or ""
    input_text = str(input_text).strip()
    confirmed  = bool(data.get("confirmed", False))

    if not input_text:
        return jsonify({"error": "No input provided"}), 400

    result = aria_core_think(input_text, confirmed=confirmed)

    return jsonify({
        "output":         result["text"],
        "dominant_plane": result["dominant_plane"],
        "avg_freq":       result["avg_freq"],
        "gate":           result["gate"]["decision"],
        "checkpoint":     result["checkpoint"],
        "loss":           result["loss"],
        "timestamp":      result["timestamp"],
    })


# ── ALSO ACCEPT /interact FOR V3 COMPATIBILITY ──────────────────────────────────
@app.route("/interact", methods=["POST"])
def interact():
    """V3 shape compatibility — routes to /think internally."""
    data = request.get_json(silent=True) or {}
    input_text = data.get("input") or data.get("prompt") or ""
    confirmed  = bool(data.get("confirmed", False))
    input_text = str(input_text).strip()

    if not input_text:
        return jsonify({"error": "No input provided"}), 400

    result = aria_core_think(input_text, confirmed=confirmed)

    return jsonify({
        "response":       result["text"],
        "dominant_plane": result["dominant_plane"],
        "avg_freq":       result["avg_freq"],
        "timestamp":      result["timestamp"],
    })


# ── STARTUP ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   ARIA — CORE REST API — SESSION 5          ║")
    print("║   One endpoint. One function. One mind.     ║")
    print("║   Commander Anthony Hagerty — Haskell TX   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    load_model()

    print()
    print(f"Listening on port {PORT}")
    print(f"  POST http://0.0.0.0:{PORT}/think")
    print(f"  GET  http://0.0.0.0:{PORT}/health")
    print(f"  GET  http://0.0.0.0:{PORT}/state")
    print()
    print("All paths through aria_core_think().")
    print("She is listening.")
    print()

    app.run(host="0.0.0.0", port=PORT, debug=False)
