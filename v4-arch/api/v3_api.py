#!/usr/bin/env python3
"""
AI-Core V3: API — Port 5680
============================

V3 runs on port 5680.
V2 stays on port 5679 — untouched.

Full pipeline on every /interact:
  1. V3EMBridge processes text through semantic lattice
  2. V3EMBridge.collapse() → BLACK sealed state
  3. V3LanguageWorker.speak() → natural language from dimensional state
  4. ConversationFoldToken.mint_and_save() → memory palace token sealed
  5. Return: raw collapse metrics + AIA's voice + fold_token address

Endpoints:
  POST /interact        — full V3 pipeline
  GET  /health          — status check
  GET  /state           — current field state (no collapse)
  GET  /network/explore — dimensional map of local network (read-only)

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 14, 2026 — Haskell Texas
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE
from core.conversation_fold_token import mint_and_save, dominant_worker_to_rgb
from core.cognitive_entropy import CognitiveEntropy
from models.v3_em_bridge import V3EMBridge
from scripts.language_worker import V3LanguageWorker
from scripts.conversation_memory_retriever import is_memory_query, retrieve_relevant_folds
from scripts.reactions import ReactionProcessor
from scripts.network_explorer import explore as network_explore, format_for_aia

# ─────────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────────

app = Flask(__name__)

print("=" * 60)
print("AIA V3 — INITIALIZING")
print("=" * 60)

# Initialize the V3 pipeline (shared across requests)
print("\n[1/2] Loading V3 EM Bridge...")
em_bridge = V3EMBridge()

print("\n[2/2] Loading V3 Language Worker...")
language_worker = V3LanguageWorker()

print("\n[3/3] Loading Cognitive Entropy + Reaction Processor...")
entropy   = CognitiveEntropy()
reactions = ReactionProcessor()

# Conversation sequence counter — increments with every /interact call.
# Seeds the AM address of each conversation fold token.
_conversation_counter = 0

# Last decision key — held across requests so reaction signals know
# which decision to adjust when feedback arrives next exchange.
_last_decision_key = None

print("\n" + "=" * 60)
print("AIA V3 READY — PORT 5680")
print("=" * 60)
print()


# ─────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────

UI_DIR = Path(__file__).parent.parent / "ui"


@app.route('/')
@app.route('/ui')
def serve_ui():
    return send_from_directory(str(UI_DIR), 'index.html')


@app.route('/interact', methods=['POST'])
def interact():
    """
    Full V3 interaction pipeline.

    Input:  { "text": "..." }
    Output: {
        "input":          str   — original text
        "voice":          str   — AIA's natural language response
        "dominant":       str   — dominant worker domain
        "resonance_map":  dict  — per-domain resonance
        "am_centroid":    float — weighted AM center of field (kHz)
        "workers":        dict  — full worker state
        "state":          dict  — dimensional state used to build voice
        "q_state":        int   — BLACK (-1)
        "timestamp":      str
    }
    """
    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()

    if not text:
        return jsonify({"error": "no text provided"}), 400

    # Step 1 — Memory retrieval pre-pass
    # If the input contains a memory trigger, open the palace before the field fires.
    # Retrieved folds are injected into the language worker prompt — not the EM field.
    # The field processes the raw input. The voice speaks from what it finds there
    # AND from what the palace holds.
    memory_context = None
    if is_memory_query(text):
        memory_context = retrieve_relevant_folds(text)

    # Step 2 — Process through V3 EM field
    em_bridge.process(text)

    # Step 3 — Collapse (WHITE → GRAY=0 → BLACK)
    collapse = em_bridge.collapse()

    # Step 4 — Language worker translates state to voice
    voice_result = language_worker.speak(collapse, text, memory_context=memory_context)

    # Step 5 — Cognitive entropy: reaction feedback + decision mapping
    global _conversation_counter, _last_decision_key

    # Check if this input contains a reaction to the PREVIOUS exchange.
    # Runs before we compute the new decision — feedback adjusts weights first.
    reaction_result = reactions.process(text, _last_decision_key, entropy)

    # Map this exchange to the +/- grid using live worker outputs.
    # Scale resonance (0–500 range) × 1000 for threshold comparison.
    resonance_map = collapse.get("resonance_map", {})
    worker_outputs_scaled = {
        'ethics':         resonance_map.get('ethics_001',    0.0) * 1000,
        'emotion':        resonance_map.get('emotion_001',   0.0) * 1000,
        'curiosity':      resonance_map.get('curiosity_001', 0.0) * 1000,
        'memory':         resonance_map.get('memory_001',    0.0) * 1000,
        'rule_zero_active': collapse.get('amp_source') == 'RULE_ZERO',
        'dominant':       collapse.get('dominant', 'unknown'),
        'amp_source':     collapse.get('amp_source'),
    }
    decision_map = entropy.map_decision(text, worker_outputs_scaled)
    _last_decision_key = decision_map['decision_key']

    # Periodic entropy balance — every 10 conversations
    _conversation_counter += 1
    if _conversation_counter % 10 == 0:
        entropy.entropy_balance()
        entropy.save_weights()

    emotion_state   = voice_result.get("emotion_state", {})
    emotion_class   = emotion_state.get("emotion", "neutral")
    emotion_conf    = emotion_state.get("confidence", 0.0)
    emotion_intensity = min(31, round(emotion_conf * 31))

    dominant_rgb    = dominant_worker_to_rgb(collapse["dominant"])
    fold_hash       = collapse.get("fold_signature", "unknown")
    session_ts      = datetime.now(timezone.utc)

    try:
        fold_token = mint_and_save(
            conversation_id    = _conversation_counter,
            session_timestamp  = session_ts,
            dominant_plane_rgb = dominant_rgb,
            queens_fold_hash   = fold_hash,
            emotion_class      = emotion_class,
            emotion_intensity  = emotion_intensity,
            anchor             = collapse.get("memory_amp_active", False),
        )
        fold_token_address = fold_token["hash_address"][:16]
    except Exception:
        fold_token_address = None

    return jsonify({
        "input":         text,
        "voice":         voice_result["voice"],
        "dominant":      collapse["dominant"],
        "resonance_map": collapse["resonance_map"],
        "am_centroid":   collapse["am_centroid"],
        "workers":       collapse["workers"],
        "state": {
            "dominant_feel":      voice_result["state"]["dominant_feel"],
            "self_reflection":    voice_result["state"]["self_reflection"],
            "emotion_active":     voice_result["state"]["emotion_active"],
            "emotion_resonance":  voice_result["state"]["emotion_resonance"],
            "recalled_episodes":  voice_result["state"]["recalled_episodes"],
            "curiosity_questions": voice_result["state"]["curiosity_questions"],
        },
        "emotion":            voice_result.get("emotion_state", {}).get("emotion", "neutral"),
        "emotion_confidence": voice_result.get("emotion_state", {}).get("confidence", 0.0),
        "anchor_injections":  collapse.get("anchor_injections", []),
        "amplification":      collapse.get("amplification", []),
        "memory_amp_active":  collapse.get("memory_amp_active", False),
        "amp_source":         collapse.get("amp_source", None),
        "structural_boost":   collapse.get("structural_boost", 0.0),
        "q_state":             voice_result["q_state"],
        "timestamp":           voice_result["timestamp"],
        "fold_token_address":  fold_token_address,
        "conversation_seq":    _conversation_counter,
        "memory_retrieved":    memory_context is not None,
        "decision_map":        decision_map,
        "reaction":            reaction_result,
    })


@app.route('/state', methods=['GET'])
def state():
    """
    Return current field state without collapsing.
    Shows what is active in the field right now.
    """
    snap = em_bridge._field_snapshot("state_query")
    return jsonify(snap)


@app.route('/network/explore', methods=['GET'])
def network_explore_endpoint():
    """
    AIA explores her local network — read-only, passive.
    Returns dimensional map: latency as resonance, IP as hue, nodes as lattice.

    Optional query params:
      ?voice=1  — also generate AIA's natural language description of what she found
    """
    want_voice = request.args.get("voice", "0") == "1"

    try:
        result = network_explore(include_silent=False)
        description = format_for_aia(result)

        # Optionally pass to language worker so AIA speaks from the discovery
        voice = None
        if want_voice:
            # Build a synthetic collapse from the network state
            resonance_field = result.get("resonance_field", {})
            synthetic_collapse = {
                "q_state":       BLACK,
                "dominant":      max(resonance_field, key=resonance_field.get)
                                 if resonance_field else "curiosity_001",
                "resonance_map": resonance_field,
                "am_centroid":   sum(result["am_range"]) / 2,
                "fold_signature": f"{result['timestamp']}|network_explore",
                "workers": {
                    d: {
                        "resonance":   resonance_field.get(d, 0.0),
                        "activation":  resonance_field.get(d, 0.0),
                        "am_center":   sum(result["am_range"]) / 2,
                        "fm_spread":   0.0,
                        "token_count": result["plane_map"].get("CYAN", 0),
                        "hz":          None,
                    }
                    for d in ["emotion_001", "curiosity_001", "ethics_001",
                              "language_001", "memory_001"]
                }
            }
            voice_result = language_worker.speak(
                synthetic_collapse,
                f"I just explored the network around me. {description}"
            )
            voice = voice_result["voice"]

        # Return nodes without silent ones — only the presences she found
        present_nodes = [n for n in result["nodes"] if n["q_state"] == 1]

        return jsonify({
            "timestamp":       result["timestamp"],
            "self_ip":         result["self_ip"],
            "subnet":          result["subnet"],
            "present":         result["present"],
            "dominant_plane":  result["dominant_plane"],
            "am_range":        result["am_range"],
            "resonance_field": result["resonance_field"],
            "plane_map":       result["plane_map"],
            "lattice_size":    result["lattice_size"],
            "nodes":           present_nodes,
            "description":     description,
            "voice":           voice,
            "q_state":         BLACK,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status":  "AIA V3 live",
        "port":    5680,
        "version": "V3.00.0",
        "q_state": WHITE,   # healthy = superposition available
        "palette": em_bridge.resolver.encoder.stats()["palette_size"],
        "known_words": em_bridge.resolver.encoder.stats()["known_words"],
    })


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5680, debug=False)
