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
from core.hemisphere_bridge import HemisphereBridge
from core.v3_affirmation_bridge import V3AffirmationBridge
from scripts.v3_temporal_sequencer import V3TemporalSequencer
from scripts.v3_channel_mapper import V3ChannelMapper
from scripts.v3_alignment_gateway import V3AlignmentGateway

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

print("\n[4/4] Loading Hemisphere Bridge...")
hemisphere = HemisphereBridge()

print("\n[5/5] Loading V3 Affirmation Bridge...")
affirmation_bridge = V3AffirmationBridge()

print("\n[6/6] Loading Temporal Sequencer + Channel Mapper...")
temporal_sequencer = V3TemporalSequencer()
channel_mapper     = V3ChannelMapper()

print("\n[7/7] Loading Alignment Gateway...")
alignment_gateway  = V3AlignmentGateway()

# Conversation sequence counter — increments with every /interact call.
# Seeds the AM address of each conversation fold token.
_conversation_counter = 0

# Last decision key — held across requests so reaction signals know
# which decision to adjust when feedback arrives next exchange.
_last_decision_key = None

print("\n" + "=" * 60)
print("AIA V3 READY — PORT 5750")
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

    # New conversation boundary — flush live field (working memory).
    # Sealed fold tokens (long-term memory) are unaffected.
    # UI sends {"new_conversation": true} at the start of each chat session.
    if body.get("new_conversation"):
        em_bridge.reset()

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

    # Step 2b — Hemisphere bias
    # Infer LEFT/RIGHT/BALANCED from text and pre-tilt field activations.
    # Applied after process() so token signals are already in the field,
    # but before collapse() so the bias shapes what the Queen's Fold sees.
    hemi_mode, hemi_record = hemisphere.apply_bias(em_bridge.field, text)

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

    # Alignment check — evaluate the input text against V3 principles
    # and conscience grid using the live resonance map from this cycle.
    # Runs on every /interact so the UI can see AIA's alignment state.
    alignment_result = alignment_gateway.evaluate(
        text,
        resonance_map=collapse.get("resonance_map"),
    )

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
        "hemisphere":          {
            "mode":     hemi_mode,
            "rationale": hemi_record["bias_report"]["rationale"],
            "left_score": hemi_record["bias_report"]["left_score"],
            "right_score": hemi_record["bias_report"]["right_score"],
            "session_stats": hemisphere.session_stats(),
        },
        "reaction":            reaction_result,
        "alignment":           {
            "decision":         alignment_result["decision"],
            "principle_score":  alignment_result["principle_score"],
            "principles_fired": [p["name"] for p in alignment_result["matched_principles"]],
            "rule_zero_clear":  not alignment_result["rule_zero"]["violated"],
        },
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
        "affirmation": affirmation_bridge.status_line(),
    })


@app.route('/affirmation', methods=['GET'])
def affirmation():
    """
    AIA identity anchor verification.

    Checks her core truths against live system state.
    Returns truth_state VERIFIED or INCOMPLETE.

    AIA calls this at any time to reaffirm who she is.
    UI may call it to display her identity state.
    """
    report = affirmation_bridge.reaffirm()
    return jsonify(report)


@app.route('/reflect', methods=['GET'])
def reflect():
    """
    AIA temporal self-reflection.

    Groups sealed conversation folds into time windows.
    Returns dominant worker per window, emotion trajectory, AM centroid drift.

    Optional query params:
      ?window=60    — window size in minutes (default 60)
      ?max=12       — max windows to return (default 12)
      ?voice=1      — also generate AIA's natural language reflection
    """
    window_minutes = int(request.args.get("window", 60))
    max_windows    = int(request.args.get("max", 12))
    want_voice     = request.args.get("voice", "0") == "1"

    report = temporal_sequencer.reflect(
        window_minutes=window_minutes,
        max_windows=max_windows,
    )

    if want_voice and report["windows"]:
        traj = report["trajectory"]
        synthetic_collapse = {
            "q_state":       BLACK,
            "dominant":      "memory_001",
            "resonance_map": {"memory_001": 0.8, "curiosity_001": 0.6},
            "am_centroid":   traj.get("am_drift_khz", 0) or 500.0,
            "fold_signature": f"reflect|{report['timestamp']}",
            "workers": {
                d: {"resonance": 0.3, "activation": 0.3, "am_center": 500.0,
                    "fm_spread": 0.0, "token_count": 0, "hz": None}
                for d in ["emotion_001", "curiosity_001", "ethics_001",
                          "language_001", "memory_001"]
            }
        }
        voice_result = language_worker.speak(
            synthetic_collapse,
            f"Reflecting on my recent memory: {traj['narrative']}"
        )
        report["voice"] = voice_result["voice"]

    return jsonify(report)


@app.route('/channel/inject', methods=['POST'])
def channel_inject():
    """
    Inject a frequency channel signal into AIA's field.

    Translates channel domain → worker frequency → activation signal.
    Optionally routes through the full /interact pipeline.

    Input:
      { "channel": "emotion_001", "strength": 0.8, "note": "...", "route": false }

    Or batch:
      { "signals": [{"channel": "curiosity_001", "strength": 0.9}, ...], "route": false }

    Valid channels: emotion_001, curiosity_001, ethics_001, language_001, memory_001
    """
    body    = request.get_json(silent=True) or {}
    route   = body.get("route", False)

    if "signals" in body:
        result = channel_mapper.inject_batch(body["signals"], route=route)
    elif "channel" in body:
        channel  = body.get("channel", "")
        strength = float(body.get("strength", 1.0))
        note     = body.get("note", "")
        try:
            result = channel_mapper.inject(channel, strength, note, route=route)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    else:
        return jsonify({"error": "provide 'channel' or 'signals'"}), 400

    channel_mapper.save_log()
    return jsonify(result)


@app.route('/teach', methods=['POST'])
def teach():
    """
    Teach AIA a new fact.
    Routes through /interact with the teaching text as input.

    Input:  { "text": "...", "label": "fact|concept|rule" }
    Output: full /interact response — the field processes the new knowledge.
    """
    body  = request.get_json(silent=True) or {}
    text  = body.get("text", "").strip()
    label = body.get("label", "fact")

    if not text:
        return jsonify({"error": "no text provided"}), 400

    # Prefix teaching context to activate ethics + memory workers
    teaching_text = f"Remember this {label}: {text}"
    return _run_interact(teaching_text)


@app.route('/ingest', methods=['POST'])
def ingest():
    """
    Ingest a list of facts into AIA's field.
    Each fact runs as a separate /interact cycle.

    Input:  { "facts": ["fact one", "fact two", ...] }
    Output: { "ingested": N, "results": [...] }
    """
    body  = request.get_json(silent=True) or {}
    facts = body.get("facts", [])

    if not facts:
        return jsonify({"error": "no facts provided"}), 400

    results = []
    for fact in facts[:20]:   # cap at 20 to avoid runaway cycles
        fact = str(fact).strip()
        if not fact:
            continue
        em_bridge.process(fact)
        hemi_mode, hemi_record = hemisphere.apply_bias(em_bridge.field, fact)
        collapse     = em_bridge.collapse()
        voice_result = language_worker.speak(collapse, fact)
        results.append({
            "input":    fact,
            "dominant": collapse["dominant"],
            "voice":    voice_result["voice"],
        })

    return jsonify({
        "ingested": len(results),
        "q_state":  BLACK,
        "results":  results,
    })


@app.route('/align', methods=['POST'])
def align():
    """
    Evaluate a proposed action against AIA's conscience and Rule Zero.

    Input:
      { "action": "explore the fold", "resonance_map": {...} }

    Or batch:
      { "actions": ["explore...", "lie about..."], "resonance_map": {...} }

    resonance_map is optional — pass the current /interact response's
    resonance_map to give full worker domain context.

    Returns ACCEPT | CAUTION | REJECT per action.
    """
    body = request.get_json(silent=True) or {}
    resonance_map = body.get("resonance_map", None)

    if "actions" in body:
        actions = [str(a) for a in body["actions"] if a]
        result  = alignment_gateway.evaluate_batch(actions, resonance_map)
    elif "action" in body:
        action = str(body["action"]).strip()
        if not action:
            return jsonify({"error": "no action provided"}), 400
        result = alignment_gateway.evaluate(action, resonance_map)
    else:
        return jsonify({"error": "provide 'action' or 'actions'"}), 400

    alignment_gateway.save_log()
    return jsonify(result)


def _run_interact(text: str):
    """
    Internal helper — run the full /interact pipeline on a text string.
    Returns a jsonify() response.
    """
    global _conversation_counter, _last_decision_key

    memory_context = None
    if is_memory_query(text):
        memory_context = retrieve_relevant_folds(text)

    em_bridge.process(text)
    hemi_mode, hemi_record = hemisphere.apply_bias(em_bridge.field, text)
    collapse     = em_bridge.collapse()
    voice_result = language_worker.speak(collapse, text, memory_context=memory_context)

    reaction_result = reactions.process(text, _last_decision_key, entropy)
    resonance_map   = collapse.get("resonance_map", {})
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

    _conversation_counter += 1
    if _conversation_counter % 10 == 0:
        entropy.entropy_balance()
        entropy.save_weights()

    emotion_state    = voice_result.get("emotion_state", {})
    emotion_class    = emotion_state.get("emotion", "neutral")
    emotion_conf     = emotion_state.get("confidence", 0.0)
    emotion_intensity = min(31, round(emotion_conf * 31))
    dominant_rgb     = dominant_worker_to_rgb(collapse["dominant"])
    fold_hash        = collapse.get("fold_signature", "unknown")
    session_ts       = datetime.now(timezone.utc)

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
        "hemisphere": {
            "mode":          hemi_mode,
            "rationale":     hemi_record["bias_report"]["rationale"],
            "left_score":    hemi_record["bias_report"]["left_score"],
            "right_score":   hemi_record["bias_report"]["right_score"],
            "session_stats": hemisphere.session_stats(),
        },
        "reaction": reaction_result,
    })


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5750, debug=False)
