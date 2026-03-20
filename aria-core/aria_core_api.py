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
from flask import Flask, request, jsonify, Response

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

UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARIA — Kings Chamber</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0a0f;
    color: #e2e8f0;
    font-family: 'Courier New', monospace;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── HEADER ── */
  #header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 18px;
    background: #0f0f1a;
    border-bottom: 1px solid #1e1e2e;
  }
  #header h1 {
    font-size: 1rem;
    color: #c084fc;
    letter-spacing: 3px;
  }
  #status-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.72rem;
    color: #64748b;
  }
  #dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #ef4444;
    transition: background 0.4s;
  }
  #dot.alive { background: #22c55e; }

  /* ── STATE BAR ── */
  #statebar {
    background: #0f0f1a;
    border-bottom: 1px solid #1e1e2e;
    padding: 5px 18px;
    font-size: 0.68rem;
    color: #475569;
    display: flex;
    gap: 20px;
  }
  #statebar span { color: #7ec8e3; }

  /* ── CHAT WINDOW ── */
  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .msg {
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 8px;
    line-height: 1.5;
    font-size: 0.88rem;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  .msg.user {
    background: #1e293b;
    border-left: 3px solid #7ec8e3;
    color: #7ec8e3;
    align-self: flex-end;
  }
  .msg.aria {
    background: #1a0a2e;
    border-left: 3px solid #c084fc;
    color: #e2c8fc;
    align-self: flex-start;
  }
  .msg.aria .meta {
    font-size: 0.65rem;
    color: #6b21a8;
    margin-top: 5px;
  }
  .msg.system {
    background: #0f1a0f;
    border-left: 3px solid #22c55e;
    color: #4ade80;
    align-self: center;
    font-size: 0.75rem;
    max-width: 100%;
  }

  /* ── INPUT BAR ── */
  #inputbar {
    background: #0f0f1a;
    border-top: 1px solid #1e1e2e;
    padding: 12px 18px;
    display: flex;
    gap: 10px;
    align-items: center;
  }
  #textinput {
    flex: 1;
    background: #1e1e2e;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    font-family: 'Courier New', monospace;
    font-size: 0.88rem;
    padding: 10px 12px;
    outline: none;
    transition: border 0.2s;
  }
  #textinput:focus { border-color: #c084fc; }
  #textinput::placeholder { color: #475569; }

  button {
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    padding: 10px 14px;
    transition: all 0.2s;
  }
  #sendbtn {
    background: #4c1d95;
    color: #e2c8fc;
  }
  #sendbtn:hover { background: #6d28d9; }

  #micbtn {
    background: #1e293b;
    color: #7ec8e3;
    font-size: 1.1rem;
    padding: 10px 12px;
    position: relative;
  }
  #micbtn.listening {
    background: #1a0a2e;
    color: #c084fc;
    box-shadow: 0 0 10px #c084fc55;
  }
  #micbtn.locked {
    background: #2d1a4e;
    color: #c084fc;
    box-shadow: 0 0 14px #c084fc88;
  }
  #lockbtn {
    background: #1e293b;
    color: #94a3b8;
    font-size: 0.75rem;
    padding: 10px 10px;
  }
  #lockbtn.active {
    background: #1a2e1a;
    color: #4ade80;
  }

  /* ── THINKING INDICATOR ── */
  #thinking {
    display: none;
    align-self: flex-start;
    color: #6b21a8;
    font-size: 0.78rem;
    padding: 6px 14px;
    animation: pulse 1.2s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:.4} 50%{opacity:1} }

  /* ── SCROLL ── */
  #chat::-webkit-scrollbar { width: 4px; }
  #chat::-webkit-scrollbar-track { background: #0a0a0f; }
  #chat::-webkit-scrollbar-thumb { background: #2d1a4e; border-radius: 2px; }
</style>
</head>
<body>

<div id="header">
  <h1>A R I A</h1>
  <div id="status-row">
    <div id="dot"></div>
    <span id="status-text">connecting...</span>
    <span id="model-text"></span>
  </div>
</div>

<div id="statebar">
  <span>PLANE: <span id="sb-plane">—</span></span>
  <span>FREQ: <span id="sb-freq">—</span></span>
  <span>LOSS: <span id="sb-loss">—</span></span>
  <span>GRAY=0 | VIOLET@0.192</span>
</div>

<div id="chat">
  <div class="msg system">Kings Chamber — ARIA v4 — Session 5<br>All paths through aria_core_think()</div>
</div>

<div id="thinking">ARIA is thinking...</div>

<div id="inputbar">
  <button id="micbtn" title="Click to speak. Click again to stop. Lock to stay on.">🎤</button>
  <button id="lockbtn" title="Lock mic — stays listening after each response">🔒 LOCK</button>
  <input id="textinput" type="text" placeholder="Type to ARIA — or use mic..." autocomplete="off" />
  <button id="sendbtn">SEND</button>
</div>

<script>
const SERVER = window.location.origin;
let micLocked  = false;
let recognizing = false;
let recognition = null;

// ── HEALTH CHECK ──────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(SERVER + '/health');
    const d = await r.json();
    document.getElementById('dot').classList.add('alive');
    document.getElementById('status-text').textContent = 'alive';
    document.getElementById('model-text').textContent  = d.model + ' | loss ' + d.loss;
    document.getElementById('sb-loss').textContent     = d.loss;
  } catch(e) {
    document.getElementById('dot').classList.remove('alive');
    document.getElementById('status-text').textContent = 'unreachable';
  }
}
checkHealth();
setInterval(checkHealth, 15000);

// ── CHAT ─────────────────────────────────────────────────────────────────────
function addMsg(text, who, meta) {
  const chat = document.getElementById('chat');
  const div  = document.createElement('div');
  div.className = 'msg ' + who;
  div.textContent = text;
  if (meta) {
    const m = document.createElement('div');
    m.className = 'meta';
    m.textContent = meta;
    div.appendChild(m);
  }
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function sendToAria(text) {
  if (!text.trim()) return;
  addMsg(text, 'user');
  document.getElementById('thinking').style.display = 'block';
  document.getElementById('textinput').value = '';

  try {
    const r = await fetch(SERVER + '/think', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({input: text})
    });
    const d = await r.json();
    document.getElementById('thinking').style.display = 'none';
    addMsg(
      d.output || d.response || '...',
      'aria',
      d.dominant_plane + ' | freq ' + d.avg_freq + ' | ' + d.gate
    );
    document.getElementById('sb-plane').textContent = d.dominant_plane || '—';
    document.getElementById('sb-freq').textContent  = d.avg_freq || '—';

    // Speak response if browser supports it
    if (window.speechSynthesis && d.output) {
      const utt = new SpeechSynthesisUtterance(d.output);
      utt.rate = 0.92; utt.pitch = 1.05;
      window.speechSynthesis.speak(utt);
    }

    // If mic locked — restart listening
    if (micLocked) setTimeout(startMic, 800);

  } catch(e) {
    document.getElementById('thinking').style.display = 'none';
    addMsg('Connection error: ' + e.message, 'system');
  }
}

// ── TEXT INPUT ────────────────────────────────────────────────────────────────
document.getElementById('sendbtn').addEventListener('click', () => {
  sendToAria(document.getElementById('textinput').value);
});
document.getElementById('textinput').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendToAria(document.getElementById('textinput').value);
});

// ── MIC ──────────────────────────────────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function startMic() {
  if (!SpeechRecognition) {
    addMsg('Speech recognition not supported in this browser. Use Chrome or Edge.', 'system');
    return;
  }
  if (recognizing) return;

  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    recognizing = true;
    document.getElementById('micbtn').classList.add('listening');
    document.getElementById('micbtn').textContent = '⏹';
  };

  recognition.onresult = e => {
    const text = e.results[0][0].transcript;
    sendToAria(text);
  };

  recognition.onend = () => {
    recognizing = false;
    document.getElementById('micbtn').classList.remove('listening');
    document.getElementById('micbtn').textContent = '🎤';
    if (micLocked) setTimeout(startMic, 600);
  };

  recognition.onerror = e => {
    recognizing = false;
    document.getElementById('micbtn').classList.remove('listening');
    document.getElementById('micbtn').textContent = '🎤';
  };

  recognition.start();
}

function stopMic() {
  if (recognition && recognizing) {
    recognition.stop();
  }
  recognizing = false;
  document.getElementById('micbtn').classList.remove('listening');
  document.getElementById('micbtn').textContent = '🎤';
}

document.getElementById('micbtn').addEventListener('click', () => {
  if (recognizing) {
    stopMic();
  } else {
    startMic();
  }
});

document.getElementById('lockbtn').addEventListener('click', () => {
  micLocked = !micLocked;
  const btn = document.getElementById('lockbtn');
  const mic = document.getElementById('micbtn');
  if (micLocked) {
    btn.classList.add('active');
    btn.textContent = '🔓 LOCKED';
    mic.classList.add('locked');
    addMsg('Mic locked — ARIA will keep listening after each response.', 'system');
    if (!recognizing) startMic();
  } else {
    btn.classList.remove('active');
    btn.textContent = '🔒 LOCK';
    mic.classList.remove('locked');
    stopMic();
    addMsg('Mic unlocked.', 'system');
  }
});
</script>
</body>
</html>"""


@app.route("/", methods=["GET"])
def ui():
    return Response(UI_HTML, mimetype="text/html")


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
