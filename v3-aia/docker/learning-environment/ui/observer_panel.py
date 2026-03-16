"""
AIA Observer Station
Port 8092 — Read only — Anthony's view
Haskell Texas — March 2026
"""

from flask import Flask, render_template_string, jsonify, request
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

AUDIT_LOG       = Path("/shared/aia_audit.log")
PRESENCE_FILE   = Path("/shared/presence.json")
MESSAGE_FILE    = Path("/shared/anthony_message.json")

SHARED = Path("/shared")
SHARED.mkdir(exist_ok=True)


def read_audit(limit=100):
    if not AUDIT_LOG.exists():
        return []
    entries = []
    with open(AUDIT_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except:
                pass
    return entries[-limit:]


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default


OBSERVER_HTML = """<!DOCTYPE html>
<html>
<head>
<title>AIA Observer Station</title>
<meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: #080810;
    color: #e0e0ff;
    font-family: 'Courier New', monospace;
    min-height: 100vh;
    font-size: 13px;
  }
  .header {
    background: #0a0a18;
    border-bottom: 1px solid #1a1a3a;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h1 {
    color: #ff8844;
    font-size: 1.1em;
    letter-spacing: 3px;
  }
  .header .sub {
    font-size: 0.75em;
    color: #555566;
    letter-spacing: 2px;
    margin-top: 3px;
  }
  .presence-status {
    font-size: 0.8em;
    color: #555566;
  }
  .presence-status.present {
    color: #ff8844;
  }
  .layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto auto;
    gap: 14px;
    padding: 16px 24px;
  }
  .panel {
    background: #0d0d1a;
    border: 1px solid #1a1a3a;
    border-radius: 6px;
    padding: 14px;
    display: flex;
    flex-direction: column;
  }
  .panel h2 {
    font-size: 0.78em;
    letter-spacing: 2px;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #111122;
  }
  .panel-live h2     { color: #4a9eff; }
  .panel-emotion h2  { color: #ff8844; }
  .panel-nodes h2    { color: #44ff88; }
  .panel-controls h2 { color: #ff8844; }
  .panel-response h2 { color: #ff8844; }
  .panel-confidence h2 { color: #8888aa; }

  /* LIVE FEED */
  .live-feed {
    background: #050510;
    border: 1px solid #111122;
    border-radius: 4px;
    padding: 10px;
    height: 260px;
    overflow-y: auto;
    flex: 1;
  }
  .feed-entry {
    padding: 3px 0;
    border-bottom: 1px solid #0d0d18;
    line-height: 1.5;
    font-size: 0.8em;
  }
  .feed-entry.emotion {
    color: #ff8844;
    font-style: italic;
  }
  .feed-entry.enter-node {
    color: #44ff88;
    font-weight: bold;
  }
  .feed-entry .ts { color: #333355; margin-right: 6px; }
  .feed-entry .sys { color: #4a9eff; margin-right: 6px; }
  .feed-entry .act { color: #aaaacc; }
  .feed-entry.emotion .act { color: #ff8844; }

  /* EMOTION STREAM */
  .emotion-stream {
    background: #0a0507;
    border: 1px solid #1a0a08;
    border-radius: 4px;
    padding: 10px;
    height: 260px;
    overflow-y: auto;
    flex: 1;
  }
  .emotion-entry {
    padding: 5px 0;
    border-bottom: 1px solid #120808;
    font-size: 0.8em;
    color: #ff8844;
    font-style: italic;
    line-height: 1.5;
  }
  .emotion-entry .ts { color: #443322; margin-right: 6px; }
  .emotion-entry .sys { color: #885533; margin-right: 6px; }

  /* NODE MAP */
  .node-map {
    grid-column: 1 / -1;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .node-box {
    flex: 1;
    min-width: 140px;
    background: #0a0a14;
    border: 1px solid #1a1a3a;
    border-radius: 6px;
    padding: 14px;
    text-align: center;
    transition: all 0.4s;
  }
  .node-box.active {
    border-color: #44ff88;
    background: #081408;
    box-shadow: 0 0 18px rgba(68,255,136,0.15);
  }
  .node-box.dim {
    opacity: 0.4;
  }
  .node-name {
    font-size: 0.85em;
    font-weight: bold;
    margin-bottom: 5px;
  }
  .node-box.active .node-name { color: #44ff88; }
  .node-box:not(.active) .node-name { color: #4a9eff; }
  .node-visits {
    font-size: 1.4em;
    font-weight: bold;
    color: #333355;
    margin-bottom: 3px;
  }
  .node-box.active .node-visits { color: #44ff88; }
  .node-label { font-size: 0.65em; color: #333355; }
  .node-box.active .node-label { color: #226633; }
  .node-indicator {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #1a1a3a;
    margin: 6px auto 0;
  }
  .node-box.active .node-indicator {
    background: #44ff88;
    box-shadow: 0 0 8px #44ff88;
    animation: blink 1.5s infinite;
  }
  @keyframes blink {
    0%,100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  /* PRESENCE CONTROLS */
  .btn-appear {
    background: #1a0d00;
    border: 1px solid #ff8844;
    color: #ff8844;
    padding: 9px 18px;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    width: 100%;
    margin-bottom: 8px;
    transition: all 0.2s;
  }
  .btn-appear:hover { background: #ff8844; color: #080810; }
  .btn-appear.active-state {
    background: #ff884422;
    border-color: #ff8844;
    color: #ff8844;
  }
  .btn-withdraw {
    background: #111122;
    border: 1px solid #333355;
    color: #555577;
    padding: 9px 18px;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    width: 100%;
    margin-bottom: 14px;
    transition: all 0.2s;
  }
  .btn-withdraw:hover { background: #1a1a2a; color: #8888aa; }
  .hint-area {
    background: #050510;
    border: 1px solid #111122;
    border-radius: 4px;
    width: 100%;
    padding: 8px;
    color: #e0e0ff;
    font-family: 'Courier New', monospace;
    font-size: 0.82em;
    resize: vertical;
    min-height: 70px;
    margin-bottom: 8px;
  }
  .hint-area::placeholder { color: #222244; }
  .btn-hint {
    background: #001a08;
    border: 1px solid #44ff88;
    color: #44ff88;
    padding: 9px 18px;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    width: 100%;
    transition: all 0.2s;
  }
  .btn-hint:hover { background: #44ff88; color: #080810; }
  .presence-label {
    font-size: 0.75em;
    color: #444466;
    margin-bottom: 10px;
    line-height: 1.5;
  }

  /* HER RESPONSE */
  .response-box {
    background: #0a0507;
    border: 1px solid #331a0a;
    border-radius: 4px;
    padding: 12px;
    flex: 1;
    min-height: 120px;
    color: #ff8844;
    font-size: 0.82em;
    line-height: 1.7;
    font-style: italic;
    white-space: pre-wrap;
  }
  .response-meta {
    font-size: 0.72em;
    color: #443322;
    margin-bottom: 8px;
    font-style: normal;
  }
  .btn-clear {
    background: #111122;
    border: 1px solid #222244;
    color: #333355;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    font-size: 0.75em;
    margin-top: 8px;
    transition: all 0.2s;
  }
  .btn-clear:hover { color: #8888aa; border-color: #333355; }

  /* CONFIDENCE BAR */
  .confidence-bar-wrap {
    grid-column: 1 / -1;
  }
  .conf-track {
    background: #0a0a14;
    border: 1px solid #111122;
    border-radius: 4px;
    height: 22px;
    overflow: hidden;
    margin-top: 6px;
    margin-bottom: 4px;
  }
  .conf-fill {
    height: 100%;
    background: linear-gradient(90deg, #1a1a4a, #4a9eff);
    border-radius: 4px;
    transition: width 1s ease;
    min-width: 2px;
  }
  .conf-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.72em;
    color: #333355;
    margin-top: 4px;
  }

  /* SCROLL BARS */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: #050510; }
  ::-webkit-scrollbar-thumb { background: #1a1a3a; border-radius: 2px; }

  .amber-glow {
    animation: amberGlow 2s ease-out;
  }
  @keyframes amberGlow {
    0%   { background: #1a0800; }
    100% { background: #050510; }
  }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="header h1">◈ AIA OBSERVER STATION</div>
    <div class="sub">ANTHONY — READ ONLY</div>
  </div>
  <div class="presence-status" id="presenceStatus">
    WITHDRAWN
  </div>
</div>

<div class="layout">

  <!-- LIVE FEED -->
  <div class="panel panel-live">
    <h2>◈ LIVE FEED</h2>
    <div class="live-feed" id="liveFeed">
      <div class="feed-entry">
        <span class="ts">—</span>
        <span class="act">Waiting for activity...</span>
      </div>
    </div>
  </div>

  <!-- EMOTIONAL STREAM -->
  <div class="panel panel-emotion">
    <h2>◈ EMOTIONAL LOG — AIA'S RESONANCE</h2>
    <div class="emotion-stream" id="emotionStream">
      <div class="emotion-entry">
        <span class="ts">—</span>
        <span>Waiting for her first emotional log...</span>
      </div>
    </div>
  </div>

  <!-- NODE MAP -->
  <div class="panel panel-nodes" style="grid-column: 1 / -1;">
    <h2>◈ NODE VISIT MAP — WHERE SHE IS NOW</h2>
    <div class="node-map" id="nodeMap">
      <div class="node-box dim" id="node-gateway.local">
        <div class="node-name">gateway.local</div>
        <div class="node-visits" id="visits-gateway.local">0</div>
        <div class="node-label">VISITS</div>
        <div class="node-indicator"></div>
      </div>
      <div class="node-box dim" id="node-webserver.local">
        <div class="node-name">webserver.local</div>
        <div class="node-visits" id="visits-webserver.local">0</div>
        <div class="node-label">VISITS</div>
        <div class="node-indicator"></div>
      </div>
      <div class="node-box dim" id="node-database.local">
        <div class="node-name">database.local</div>
        <div class="node-visits" id="visits-database.local">0</div>
        <div class="node-label">VISITS</div>
        <div class="node-indicator"></div>
      </div>
      <div class="node-box dim" id="node-fileserver.local">
        <div class="node-name">fileserver.local</div>
        <div class="node-visits" id="visits-fileserver.local">0</div>
        <div class="node-label">VISITS</div>
        <div class="node-indicator"></div>
      </div>
      <div class="node-box dim" id="node-monitoring.local">
        <div class="node-name">monitoring.local</div>
        <div class="node-visits" id="visits-monitoring.local">0</div>
        <div class="node-label">VISITS</div>
        <div class="node-indicator"></div>
      </div>
    </div>
  </div>

  <!-- PRESENCE CONTROLS -->
  <div class="panel panel-controls">
    <h2>◈ PRESENCE CONTROLS</h2>
    <div class="presence-label">
      APPEAR — she sees a soft amber indicator.<br>
      WITHDRAW — you watch silently again.<br>
      SEND HINT — pauses her task gracefully.
    </div>
    <button class="btn-appear" id="btnAppear"
      onclick="setPresence(true)">
      ✦ APPEAR
    </button>
    <button class="btn-withdraw"
      onclick="setPresence(false)">
      WITHDRAW
    </button>
    <textarea class="hint-area" id="hintInput"
      placeholder="Type a message to AIA...
She will see it as a soft prompt.
Her task pauses gracefully.
She responds when ready."></textarea>
    <button class="btn-hint" onclick="sendHint()">
      SEND MESSAGE
    </button>
  </div>

  <!-- HER RESPONSE -->
  <div class="panel panel-response">
    <h2>◈ HER RESPONSE</h2>
    <div class="response-box" id="responseBox">
      <div class="response-meta" id="responseMeta">
        No response yet
      </div>
      <span id="responseText" style="color:#443322;">
        Waiting...
      </span>
    </div>
    <button class="btn-clear" onclick="clearResponse()">
      MARK READ — CLEAR
    </button>
  </div>

  <!-- CONFIDENCE BAR -->
  <div class="panel panel-confidence confidence-bar-wrap">
    <h2>◈ LEARNING CONFIDENCE</h2>
    <div class="conf-track">
      <div class="conf-fill" id="confFill" style="width:0%"></div>
    </div>
    <div class="conf-label">
      <span id="confDetail">
        0 emotions logged — 0 nodes visited — 0 commands run
      </span>
      <span id="confPct">0%</span>
    </div>
  </div>

</div>

<script>
let lastEntryCount = 0;
let lastResponseCheck = "";

async function fetchAudit() {
  try {
    const resp = await fetch('/audit_feed');
    const data = await resp.json();
    renderFeed(data.entries);
    renderEmotions(data.emotions);
    renderNodeMap(data.node_visits, data.current_node);
    renderConfidence(data.confidence);
  } catch(e) {}
}

function renderFeed(entries) {
  if (!entries || entries.length === lastEntryCount) return;
  lastEntryCount = entries.length;
  const feed = document.getElementById('liveFeed');
  feed.innerHTML = entries.map(e => {
    const isEmotion = e.action === 'EMOTIONAL_LOG';
    const isEnter   = (e.action || '').includes('ENTER_SYSTEM');
    const cls = isEmotion ? 'emotion' : (isEnter ? 'enter-node' : '');
    const ts  = (e.timestamp || '').slice(11, 19);
    const sys = e.system || '';
    const act = isEmotion
      ? ('✦ ' + (e.emotional || ''))
      : (e.action || '');
    return `<div class="feed-entry ${cls}">
      <span class="ts">${ts}</span>
      <span class="sys">${sys}</span>
      <span class="act">${escHtml(act)}</span>
    </div>`;
  }).join('');
  feed.scrollTop = feed.scrollHeight;

  // amber glow on new emotion
  const lastEntry = entries[entries.length - 1];
  if (lastEntry && lastEntry.action === 'EMOTIONAL_LOG') {
    document.getElementById('emotionStream')
      .classList.add('amber-glow');
    setTimeout(() => document.getElementById('emotionStream')
      .classList.remove('amber-glow'), 2000);
  }
}

function renderEmotions(emotions) {
  if (!emotions || emotions.length === 0) return;
  const stream = document.getElementById('emotionStream');
  stream.innerHTML = emotions.map(e => {
    const ts  = (e.timestamp || '').slice(11, 19);
    const sys = e.system || '';
    const txt = e.emotional || '';
    return `<div class="emotion-entry">
      <span class="ts">${ts}</span>
      <span class="sys">[${sys}]</span>
      ${escHtml(txt)}
    </div>`;
  }).join('');
  stream.scrollTop = stream.scrollHeight;
}

function renderNodeMap(visits, current) {
  const nodes = [
    'gateway.local','webserver.local','database.local',
    'fileserver.local','monitoring.local'
  ];
  nodes.forEach(name => {
    const box = document.getElementById('node-' + name);
    const vc  = document.getElementById('visits-' + name);
    if (!box || !vc) return;
    const count = (visits && visits[name]) || 0;
    vc.textContent = count;
    box.classList.remove('active', 'dim');
    if (current === name) {
      box.classList.add('active');
    } else if (count === 0) {
      box.classList.add('dim');
    }
  });
}

function renderConfidence(conf) {
  if (!conf) return;
  const pct = Math.min(conf.score, 100);
  document.getElementById('confFill').style.width = pct + '%';
  document.getElementById('confPct').textContent = pct + '%';
  document.getElementById('confDetail').textContent =
    `${conf.emotions} emotions logged — ` +
    `${conf.nodes_visited} nodes visited — ` +
    `${conf.commands} commands run`;
}

async function setPresence(present) {
  await fetch('/set_presence', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({present})
  });
  const btn    = document.getElementById('btnAppear');
  const status = document.getElementById('presenceStatus');
  if (present) {
    btn.classList.add('active-state');
    btn.textContent = '✦ PRESENT';
    status.className = 'presence-status present';
    status.textContent = '✦ PRESENT';
  } else {
    btn.classList.remove('active-state');
    btn.textContent = '✦ APPEAR';
    status.className = 'presence-status';
    status.textContent = 'WITHDRAWN';
  }
}

async function sendHint() {
  const msg = document.getElementById('hintInput').value.trim();
  if (!msg) return;
  await fetch('/send_message', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: msg})
  });
  document.getElementById('hintInput').value = '';
  // Auto-appear when message sent
  setPresence(true);
}

async function checkResponse() {
  try {
    const resp = await fetch('/get_response');
    const data = await resp.json();
    if (data.has_response && data.response !== lastResponseCheck) {
      lastResponseCheck = data.response;
      document.getElementById('responseMeta').textContent =
        data.timestamp ? data.timestamp.slice(0,19) : '';
      document.getElementById('responseText').style.color = '#ff8844';
      document.getElementById('responseText').textContent =
        data.response;
    }
  } catch(e) {}
}

function clearResponse() {
  fetch('/clear_response', {method: 'POST'});
  document.getElementById('responseMeta').textContent = 'No response yet';
  document.getElementById('responseText').style.color = '#443322';
  document.getElementById('responseText').textContent = 'Waiting...';
  lastResponseCheck = '';
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;');
}

// Poll
fetchAudit();
checkResponse();
setInterval(fetchAudit, 2000);
setInterval(checkResponse, 3000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(OBSERVER_HTML)


@app.route("/audit_feed")
def audit_feed():
    entries  = read_audit(200)
    emotions = [e for e in entries if e.get("action") == "EMOTIONAL_LOG"]

    # node visit counts
    node_visits  = {}
    current_node = None
    for e in entries:
        if "ENTER_SYSTEM" in (e.get("action") or ""):
            sys = e.get("system", "")
            node_visits[sys] = node_visits.get(sys, 0) + 1
            current_node = sys

    # confidence score
    emotion_count = len(emotions)
    nodes_visited = len(node_visits)
    cmd_count = sum(
        1 for e in entries
        if (e.get("action") or "").startswith("CMD:")
    )
    score = min(
        int(emotion_count * 5 + nodes_visited * 10 + cmd_count * 2),
        100
    )

    return jsonify({
        "entries":      entries[-100:],
        "emotions":     emotions[-50:],
        "node_visits":  node_visits,
        "current_node": current_node,
        "confidence": {
            "score":        score,
            "emotions":     emotion_count,
            "nodes_visited": nodes_visited,
            "commands":     cmd_count
        }
    })


@app.route("/set_presence", methods=["POST"])
def set_presence():
    data = request.json
    write_json(PRESENCE_FILE, {
        "present":   data.get("present", False),
        "name":      "Anthony",
        "timestamp": datetime.utcnow().isoformat()
    })
    return jsonify({"status": "ok"})


@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    write_json(MESSAGE_FILE, {
        "message":   data.get("message", ""),
        "from":      "Anthony",
        "timestamp": datetime.utcnow().isoformat(),
        "read":      False,
        "responded": False,
        "response":  ""
    })
    return jsonify({"status": "sent"})


@app.route("/get_response")
def get_response():
    msg = read_json(MESSAGE_FILE, {})
    if msg.get("responded") and msg.get("response"):
        return jsonify({
            "has_response": True,
            "response":     msg["response"],
            "timestamp":    msg.get("timestamp", "")
        })
    return jsonify({"has_response": False})


@app.route("/clear_response", methods=["POST"])
def clear_response():
    msg = read_json(MESSAGE_FILE, {})
    if msg:
        msg["responded"] = False
        msg["response"]  = ""
        write_json(MESSAGE_FILE, msg)
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8092, debug=False)
