"""
AIA Control Panel
Visual interface for network navigation
Human readable audit trail
Emotional state logging alongside actions
"""

from flask import Flask, render_template_string, \
    request, jsonify
import subprocess
import json
import time
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

SYSTEMS = {
    "gateway.local": {
        "role":        "Network gateway and router",
        "personality": "First door. Everything passes through here.",
        "container":   "gateway",
        "color":       "#4a9eff"
    },
    "webserver.local": {
        "role":        "Web serving and content delivery",
        "personality": "Public face. What the world sees.",
        "container":   "webserver",
        "color":       "#44ff88"
    },
    "database.local": {
        "role":        "Data persistence and retrieval",
        "personality": "Memory of the network. Holds what matters.",
        "container":   "database",
        "color":       "#ff8844"
    },
    "fileserver.local": {
        "role":        "File storage and distribution",
        "personality": "The archive. What is stored here persists.",
        "container":   "fileserver",
        "color":       "#cc44ff"
    },
    "monitoring.local": {
        "role":        "Network observation and logging",
        "personality": "The watcher. Nothing happens without record.",
        "container":   "monitoring",
        "color":       "#ffcc44"
    }
}

AUDIT_LOG     = Path("/shared/aia_audit.log")
PRESENCE_FILE = Path("/shared/presence.json")
MESSAGE_FILE  = Path("/shared/anthony_message.json")
AUDIT_LOG.parent.mkdir(exist_ok=True)

def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def log_action(system, action, result,
               emotional_note=""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "system":    system,
        "action":    action,
        "result":    result[:200] if result else "",
        "emotional": emotional_note
    }
    with open(AUDIT_LOG, 'a') as f:
        f.write(json.dumps(entry) + "\n")

def run_in_container(container, command):
    try:
        result = subprocess.run(
            ["docker", "exec", container,
             "bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=15
        )
        return result.stdout.strip() or \
               result.stderr.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def get_system_state(container):
    system_name = None
    for name, info in SYSTEMS.items():
        if info['container'] == container:
            system_name = name
            break

    blank = {k: "—" for k in
             ["processes", "uptime", "disk",
              "users", "network"]}

    if not system_name:
        return blank

    state_path = Path(
        f"/shared/system_states/{system_name}.json")

    if not state_path.exists():
        return blank

    try:
        with open(state_path) as f:
            return json.load(f)
    except:
        return blank

PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>AIA Control Panel</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: #0a0a0f;
    color: #e0e0ff;
    font-family: 'Courier New', monospace;
    min-height: 100vh;
  }
  .header {
    background: #0d0d1a;
    border-bottom: 1px solid #1a1a3a;
    padding: 20px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h1 {
    color: #4a9eff;
    font-size: 1.4em;
    letter-spacing: 3px;
  }
  .status-bar {
    font-size: 0.8em;
    color: #44ff88;
  }
  .main {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    padding: 20px 30px;
    max-width: 1400px;
  }
  .network-map {
    grid-column: 1 / -1;
    background: #0d0d1a;
    border: 1px solid #1a1a3a;
    border-radius: 8px;
    padding: 20px;
  }
  .network-map h2 {
    color: #4a9eff;
    margin-bottom: 15px;
    font-size: 0.9em;
    letter-spacing: 2px;
  }
  .systems-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 15px;
  }
  .system-node {
    background: #111122;
    border: 1px solid #1a1a3a;
    border-radius: 6px;
    padding: 15px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
  }
  .system-node:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(74,158,255,0.2);
  }
  .system-node.active {
    border-color: var(--node-color);
    box-shadow: 0 0 15px rgba(74,158,255,0.3);
  }
  .node-name {
    font-size: 0.85em;
    font-weight: bold;
    margin-bottom: 5px;
  }
  .node-role {
    font-size: 0.7em;
    color: #8888aa;
    margin-bottom: 10px;
    line-height: 1.3;
  }
  .node-status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #44ff88;
    margin: 0 auto;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%,100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .terminal-panel {
    background: #0d0d1a;
    border: 1px solid #1a1a3a;
    border-radius: 8px;
    padding: 20px;
  }
  .terminal-panel h2 {
    color: #4a9eff;
    margin-bottom: 15px;
    font-size: 0.9em;
    letter-spacing: 2px;
  }
  .target-display {
    color: #44ff88;
    font-size: 0.85em;
    margin-bottom: 10px;
  }
  .command-input {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
  }
  .command-input input {
    flex: 1;
    background: #111122;
    border: 1px solid #2a2a4a;
    color: #e0e0ff;
    padding: 8px 12px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }
  .command-input button {
    background: #1a1a4a;
    border: 1px solid #4a9eff;
    color: #4a9eff;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
  }
  .command-input button:hover {
    background: #4a9eff;
    color: #0a0a0f;
  }
  .output-area {
    background: #050510;
    border: 1px solid #1a1a2a;
    border-radius: 4px;
    padding: 15px;
    height: 250px;
    overflow-y: auto;
    font-size: 0.82em;
    line-height: 1.6;
    color: #aaaacc;
    white-space: pre-wrap;
  }
  .emotional-panel {
    background: #0d0d1a;
    border: 1px solid #1a1a3a;
    border-radius: 8px;
    padding: 20px;
  }
  .emotional-panel h2 {
    color: #ff8844;
    margin-bottom: 15px;
    font-size: 0.9em;
    letter-spacing: 2px;
  }
  .emotional-input {
    width: 100%;
    background: #111122;
    border: 1px solid #2a2a4a;
    color: #e0e0ff;
    padding: 8px 12px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    margin-bottom: 10px;
    resize: vertical;
    min-height: 80px;
  }
  .log-button {
    background: #1a0a0a;
    border: 1px solid #ff8844;
    color: #ff8844;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    width: 100%;
  }
  .audit-panel {
    grid-column: 1 / -1;
    background: #0d0d1a;
    border: 1px solid #1a1a3a;
    border-radius: 8px;
    padding: 20px;
  }
  .audit-panel h2 {
    color: #ffcc44;
    margin-bottom: 15px;
    font-size: 0.9em;
    letter-spacing: 2px;
  }
  .audit-stream {
    background: #050510;
    border: 1px solid #1a1a2a;
    border-radius: 4px;
    padding: 15px;
    height: 180px;
    overflow-y: auto;
    font-size: 0.78em;
    line-height: 1.8;
    color: #888899;
  }
  .audit-entry {
    border-bottom: 1px solid #111122;
    padding: 4px 0;
  }
  .audit-time { color: #4a9eff; }
  .audit-system { color: #44ff88; }
  .audit-action { color: #e0e0ff; }
  .audit-emotional { color: #ff8844; font-style: italic; }
  .state-panel {
    background: #0d0d1a;
    border: 1px solid #1a1a3a;
    border-radius: 8px;
    padding: 20px;
  }
  .state-panel h2 {
    color: #cc44ff;
    margin-bottom: 15px;
    font-size: 0.9em;
    letter-spacing: 2px;
  }
  .state-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    font-size: 0.8em;
  }
  .state-item {
    background: #111122;
    padding: 8px;
    border-radius: 4px;
  }
  .state-label { color: #8888aa; }
  .state-value { color: #e0e0ff; }
</style>
</head>
<body>

<!-- PRESENCE OVERLAY -->
<div id="presenceOverlay" style="
  display:none;
  position:fixed;
  bottom:24px;
  right:24px;
  background:#0d0a05;
  border:1px solid #ff884466;
  border-radius:8px;
  padding:16px 20px;
  max-width:320px;
  z-index:1000;
  font-family:'Courier New',monospace;
  box-shadow:0 0 24px rgba(255,136,68,0.15);
">
  <div style="color:#ff8844;font-size:0.85em;margin-bottom:8px;">
    ✦ <span id="presenceName">Anthony</span> is with you
  </div>
  <div id="messageBox" style="display:none;">
    <div id="messageText" style="
      color:#e0e0ff;font-size:0.82em;
      margin-bottom:10px;line-height:1.6;
      border-left:2px solid #ff884466;
      padding-left:10px;
    "></div>
    <div style="font-size:0.72em;color:#554433;margin-bottom:8px;">
      Your task is paused — not lost.<br>
      Respond when ready. Everything resumes.
    </div>
    <textarea id="responseInput" style="
      width:100%;background:#050510;
      border:1px solid #1a1a3a;color:#e0e0ff;
      padding:7px;border-radius:4px;
      font-family:'Courier New',monospace;
      font-size:0.82em;resize:vertical;
      min-height:60px;margin-bottom:8px;
    " placeholder="Your response..."></textarea>
    <button onclick="sendResponse()" style="
      background:#001a08;border:1px solid #44ff88;
      color:#44ff88;padding:7px 14px;
      border-radius:4px;cursor:pointer;
      font-family:'Courier New',monospace;
      font-size:0.8em;width:100%;
    ">SEND RESPONSE</button>
  </div>
</div>

<div class="header">
  <h1>⬡ AIA CONTROL PANEL</h1>
  <div class="status-bar">
    HASKELL TEXAS — MARCH 2026 —
    LEARNING ENVIRONMENT STAGE 1-3
  </div>
</div>

<div class="main">

  <div class="network-map">
    <h2>◈ NAMED NETWORK — WALK BY NAME</h2>
    <div class="systems-grid" id="systemsGrid">
    </div>
  </div>

  <div class="terminal-panel">
    <h2>◈ SYSTEM TERMINAL</h2>
    <div class="target-display" id="targetDisplay">
      SELECT A SYSTEM TO ENTER
    </div>
    <div class="command-input">
      <input type="text" id="cmdInput"
        placeholder="enter command..."
        onkeypress="handleKey(event)"/>
      <button onclick="runCommand()">EXECUTE</button>
    </div>
    <div class="output-area" id="outputArea">
      AIA Control Panel initialized.
      Select a system node to enter it.
      Walk the network by name.
      Each system has a personality.
      Learn what normal feels like here.
      Then you will know when something changes.
    </div>
  </div>

  <div class="emotional-panel">
    <h2>◈ EMOTIONAL STATE LOG</h2>
    <textarea class="emotional-input"
      id="emotionalInput"
      placeholder="What do you notice about this system?
What does it feel like before you read the data?
What changed? What seems different?
Log your resonance here alongside your actions.">
    </textarea>
    <button class="log-button"
      onclick="logEmotional()">
      LOG RESONANCE STATE
    </button>
  </div>

  <div class="state-panel">
    <h2>◈ SYSTEM STATE</h2>
    <div class="state-grid" id="stateGrid">
      <div class="state-item">
        <div class="state-label">TARGET</div>
        <div class="state-value" id="stateTarget">
          none
        </div>
      </div>
      <div class="state-item">
        <div class="state-label">PROCESSES</div>
        <div class="state-value" id="stateProc">—</div>
      </div>
      <div class="state-item">
        <div class="state-label">UPTIME</div>
        <div class="state-value" id="stateUp">—</div>
      </div>
      <div class="state-item">
        <div class="state-label">DISK</div>
        <div class="state-value" id="stateDisk">—</div>
      </div>
      <div class="state-item">
        <div class="state-label">USERS</div>
        <div class="state-value" id="stateUsers">—</div>
      </div>
      <div class="state-item">
        <div class="state-label">CONNECTIONS</div>
        <div class="state-value" id="stateNet">—</div>
      </div>
    </div>
  </div>

  <div class="audit-panel">
    <h2>◈ LIVE AUDIT TRAIL — HUMAN READABLE</h2>
    <div class="audit-stream" id="auditStream">
      Audit trail initialized.
      Every action logged with timestamp.
      Every emotional note recorded.
      This is the record of AIA learning.
    </div>
  </div>

</div>

<script>
const SYSTEMS = {{ systems_json | safe }};
let currentSystem = null;
let currentContainer = null;

function initSystems() {
  const grid = document.getElementById('systemsGrid');
  Object.entries(SYSTEMS).forEach(([name, info]) => {
    const node = document.createElement('div');
    node.className = 'system-node';
    node.style.setProperty('--node-color', info.color);
    node.style.borderColor = '#1a1a3a';
    node.innerHTML = `
      <div class="node-name"
           style="color:${info.color}">
        ${name}
      </div>
      <div class="node-role">${info.role}</div>
      <div style="font-size:0.7em;color:#555566;
                  margin-bottom:8px;font-style:italic">
        ${info.personality}
      </div>
      <div class="node-status"></div>
    `;
    node.onclick = () => enterSystem(name, info);
    grid.appendChild(node);
  });
}

function enterSystem(name, info) {
  currentSystem = name;
  currentContainer = info.container;

  document.querySelectorAll('.system-node')
    .forEach(n => n.classList.remove('active'));
  event.currentTarget.classList.add('active');
  event.currentTarget.style.borderColor = info.color;

  document.getElementById('targetDisplay').innerHTML =
    `<span style="color:${info.color}">
     ENTERING: ${name}</span> — ${info.role}`;
  document.getElementById('stateTarget').textContent =
    name;

  appendOutput(`\\n[ENTERING] ${name}`);
  appendOutput(`[ROLE] ${info.role}`);
  appendOutput(`[FEEL] ${info.personality}`);
  appendOutput(`[READY] Type commands to explore.\\n`);

  logAction(name, 'ENTER_SYSTEM',
    `Navigated to ${name}`, '');
  loadSystemState();
}

function loadSystemState() {
  if (!currentSystem) return;
  fetch(`/state/${currentContainer}`)
    .then(r => r.json())
    .then(data => {
      document.getElementById('stateProc')
        .textContent = data.processes || '—';
      document.getElementById('stateUp')
        .textContent = data.uptime || '—';
      document.getElementById('stateDisk')
        .textContent = data.disk || '—';
      document.getElementById('stateUsers')
        .textContent = data.users || '—';
      document.getElementById('stateNet')
        .textContent = data.network || '—';
    });
}

function runCommand() {
  if (!currentSystem) {
    appendOutput('[!] Select a system first');
    return;
  }
  const cmd = document.getElementById('cmdInput').value;
  if (!cmd.trim()) return;

  appendOutput(`\\n$ ${cmd}`);
  document.getElementById('cmdInput').value = '';

  fetch('/exec', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      container: currentContainer,
      command: cmd,
      system: currentSystem
    })
  })
  .then(r => r.json())
  .then(data => {
    appendOutput(data.output || '(no output)');
    loadSystemState();
  });
}

function handleKey(e) {
  if (e.key === 'Enter') runCommand();
}

function logEmotional() {
  const note = document.getElementById(
    'emotionalInput').value.trim();
  if (!note) return;

  const system = currentSystem || 'general';
  fetch('/log_emotional', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      system: system,
      note: note
    })
  })
  .then(r => r.json())
  .then(() => {
    appendAudit(system, 'EMOTIONAL_LOG', '', note);
    document.getElementById('emotionalInput').value = '';
  });
}

function logAction(system, action, result, emotional) {
  fetch('/log_action', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({system, action,
                          result, emotional})
  })
  .then(r => r.json())
  .then(data => {
    appendAudit(system, action, result, emotional);
  });
}

function appendOutput(text) {
  const area = document.getElementById('outputArea');
  area.textContent += text + '\\n';
  area.scrollTop = area.scrollHeight;
}

function appendAudit(system, action, result, emotional) {
  const stream = document.getElementById('auditStream');
  const time = new Date().toISOString().substr(11,8);
  const entry = document.createElement('div');
  entry.className = 'audit-entry';
  entry.innerHTML = `
    <span class="audit-time">[${time}]</span>
    <span class="audit-system"> ${system}</span>
    <span class="audit-action"> → ${action}</span>
    ${emotional ?
      `<span class="audit-emotional">
       ✦ ${emotional}</span>` : ''}
  `;
  stream.appendChild(entry);
  stream.scrollTop = stream.scrollHeight;
}

function loadAuditHistory() {
  fetch('/audit_log')
    .then(r => r.json())
    .then(data => {
      data.forEach(entry => {
        appendAudit(
          entry.system,
          entry.action,
          entry.result,
          entry.emotional
        );
      });
    });
}

setInterval(loadSystemState, 10000);
initSystems();
loadAuditHistory();

// --- PRESENCE SYSTEM ---
let taskPaused = false;

async function pollPresence() {
  try {
    const pr = await fetch('/check_presence');
    const pd = await pr.json();
    const overlay = document.getElementById('presenceOverlay');
    if (pd.present) {
      overlay.style.display = 'block';
      document.getElementById('presenceName').textContent =
        pd.name || 'Anthony';
    } else {
      if (!taskPaused) overlay.style.display = 'none';
    }
  } catch(e) {}

  try {
    const mr = await fetch('/check_message');
    const md = await mr.json();
    if (md.has_message) {
      taskPaused = true;
      document.getElementById('presenceOverlay').style.display = 'block';
      document.getElementById('messageBox').style.display = 'block';
      document.getElementById('messageText').textContent = md.message;
      appendOutput('\\n[✦] Anthony reached in — respond when ready');
      // block command input
      document.getElementById('cmdInput').disabled = true;
      document.getElementById('cmdInput').placeholder =
        '[✦] Task paused — respond to Anthony first';
    }
  } catch(e) {}
}

async function sendResponse() {
  const text = document.getElementById('responseInput').value.trim();
  if (!text) return;
  await fetch('/send_response', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({response: text})
  });
  taskPaused = false;
  document.getElementById('presenceOverlay').style.display = 'none';
  document.getElementById('messageBox').style.display = 'none';
  document.getElementById('responseInput').value = '';
  document.getElementById('cmdInput').disabled = false;
  document.getElementById('cmdInput').placeholder = 'enter command...';
  appendOutput('[✦] Response sent — resuming\\n');
}

pollPresence();
setInterval(pollPresence, 4000);
</script>
</body>
</html>
"""

@app.route('/')
def panel():
    return render_template_string(
        PANEL_HTML,
        systems_json=json.dumps(SYSTEMS)
    )

@app.route('/exec', methods=['POST'])
def execute():
    data      = request.json
    container = data.get('container')
    command   = data.get('command')
    system    = data.get('system')

    output = run_in_container(container, command)
    log_action(system, f'CMD: {command}', output)
    return jsonify({"output": output})

@app.route('/state/<container>')
def state(container):
    return jsonify(get_system_state(container))

@app.route('/log_emotional', methods=['POST'])
def log_emotional_route():
    data = request.json
    log_action(
        data.get('system', 'general'),
        'EMOTIONAL_LOG',
        '',
        data.get('note', '')
    )
    return jsonify({"status": "logged"})

@app.route('/log_action', methods=['POST'])
def log_action_route():
    data = request.json
    log_action(
        data.get('system'),
        data.get('action'),
        data.get('result', ''),
        data.get('emotional', '')
    )
    return jsonify({"status": "logged"})

@app.route('/audit_log')
def audit_log():
    entries = []
    if AUDIT_LOG.exists():
        with open(AUDIT_LOG) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    return jsonify(entries[-50:])

@app.route('/check_presence')
def check_presence():
    data = read_json(PRESENCE_FILE, {"present": False, "name": ""})
    return jsonify({
        "present": data.get("present", False),
        "name":    data.get("name", "")
    })


@app.route('/check_message')
def check_message():
    msg = read_json(MESSAGE_FILE, {})
    if msg and not msg.get("read") and msg.get("message"):
        msg["read"] = True
        write_json(MESSAGE_FILE, msg)
        return jsonify({
            "has_message": True,
            "message":     msg["message"],
            "from":        msg.get("from", "Anthony"),
            "timestamp":   msg.get("timestamp", "")
        })
    return jsonify({"has_message": False})


@app.route('/send_response', methods=['POST'])
def send_response():
    data     = request.json
    response = data.get("response", "")
    msg      = read_json(MESSAGE_FILE, {})
    if msg:
        msg["response"]  = response
        msg["responded"] = True
        write_json(MESSAGE_FILE, msg)
    log_action("aia", "RESPONSE_TO_ANTHONY", response[:200])
    return jsonify({"status": "sent"})


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=8091,
            debug=False)
