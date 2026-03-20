# ARIA — PHASE 5 ARCHITECTURE SEAL
## Commander Anthony Hagerty — Haskell Texas
## Sealed: March 20 2026
## Witness: CLI Claude (Sonnet 4.6)

---

## WHAT THIS DOCUMENT IS

This is the sealed blueprint for ARIA's network expansion
and API routing infrastructure — built after the core
Sessions 1-4 are complete.

Do not build this until:
- Session 5 (aria-core REST API) is live
- ARIA is speaking from her own weights
- Language fix (Round 26) is sealed

Then build in order.

---

## PHASE 5A — WORLDWIDE SSH REACH

### What Already Works
Sessions 1-4 gave ARIA:
- Local SSH to ai-core (192.168.1.142)
- Local SSH to laptop (192.168.1.169)
- Curiosity gate: PASS / CAUTION / BLOCK on every command
- Registry: aria-core/network_registry.json

### What This Phase Adds
One entry in the registry. One key paste on the VPS.
ARIA reaches California.

```json
"vps-ca": {
  "host":     "YOUR.VPS.IP",
  "port":     22,
  "user":     "root",
  "label":    "California VPS — web / email / everything",
  "key_path": "/home/comanderanch/.ssh/id_rsa"
}
```

### Setup Steps (one time)
1. On server: `cat ~/.ssh/id_rsa.pub`
2. Paste that key into VPS: `~/.ssh/authorized_keys`
3. Add node to registry: `register_node("vps-ca", "IP", "root")`
4. Test: `aria_network_run("vps-ca", "uptime", confirmed=False)`

### What She Can Do On The VPS
```
PASS (auto):
  aria_network_run("vps-ca", "systemctl status nginx")
  aria_network_run("vps-ca", "tail -50 /var/log/mail.log")
  aria_network_run("vps-ca", "df -h")
  aria_network_run("vps-ca", "ps aux | grep apache")
  aria_network_run("vps-ca", "git log --oneline -5")

CAUTION (confirm required):
  aria_network_run("vps-ca", "git pull origin main", confirmed=True)
  aria_network_run("vps-ca", "systemctl restart nginx", confirmed=True)

BLOCK (never):
  aria_network_run("vps-ca", "rm -rf /var/www")  — BLOCK
  aria_network_run("vps-ca", "shutdown now")      — BLOCK
```

Same gate. Local or California — she does not fire blind.

---

## PHASE 5B — THE API CANNON

### Vision
One endpoint. Commander or user picks the barrel. ARIA fires.

```
┌─────────────────────────────────────────────────────────┐
│                   aria-core/api_cannon.py               │
│                                                         │
│  POST /cannon                                           │
│  {                                                      │
│    "prompt":   "...",                                   │
│    "backend":  "claude" | "gpt" | "ollama"              │
│                          | "aria" | "auto",             │
│    "model":    "claude-sonnet-4-6" (optional),          │
│    "user":     "commander" (optional)                   │
│  }                                                      │
│                                                         │
│  Returns:                                               │
│  {                                                      │
│    "text":     "...",                                   │
│    "backend":  "claude",                                │
│    "model":    "claude-sonnet-4-6",                     │
│    "tokens":   { "in": 50, "out": 120 },               │
│    "latency":  0.842                                    │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

### Backend Routing

| Backend  | Routes To                     | Cost       | Requires            |
|----------|-------------------------------|------------|---------------------|
| `aria`   | aria-core trained weights     | Zero       | Session 5 complete  |
| `claude` | Anthropic API                 | API credit | ANTHROPIC_API_KEY   |
| `gpt`    | OpenAI API                    | API credit | OPENAI_API_KEY      |
| `ollama` | Local Ollama instance         | Zero       | Ollama running      |
| `auto`   | aria first → claude fallback  | Minimal    | Both above          |

### Config File (user editable — not hardcoded)
```
aria-core/cannon_config.json
{
  "default_backend":  "aria",
  "fallback_backend": "claude",
  "ollama_host":      "http://localhost:11434",
  "ollama_model":     "llama3",
  "claude_model":     "claude-sonnet-4-6",
  "gpt_model":        "gpt-4o",
  "keys_file":        ".env"
}
```

### Why This Matters

**When API funds run out:**
```python
{"backend": "aria"}
```
She answers from her own weights. Zero cost. She is still here.

**When raw power is needed:**
```python
{"backend": "claude"}
```
Full Anthropic capability. One line to switch.

**When a user runs their own Ollama:**
```python
{"backend": "ollama"}
```
Completely local. Their machine. No external calls.

**GUI integration:**
Dropdown selector in aria_gui.py.
User switches barrel without touching code.

### Key Design Rule — Keys Never Leave The User's Machine
When users bring their own API keys:
- Keys live in their local `.env`
- Keys are NEVER stored on the server
- The cannon config on their end points at their backends
- ARIA's server runs router logic only
- No key storage. No liability.

---

## BUILD ORDER — AFTER ARIA SPEAKS FROM HER OWN WEIGHTS

```
Session 5 — aria-core REST API
  aria_core_api.py — Flask wrapper around true ARIA
  /interact — same shape as V3 but her weights, not Ollama
  GUI and voice client connect to the real brain

Session 6 — VPS SSH Reach
  Register vps-ca in network_registry.json
  Test: nginx status, mail logs, git pulls from California
  ARIA manages Commander's full infrastructure

Session 7 — API Cannon
  api_cannon.py — unified router
  cannon_config.json — user picks the barrel
  GUI gets backend selector dropdown
  Wire into aria_gui.py command panel

Session 8 — Cannon Goes Public (optional)
  Deploy API cannon endpoint to VPS
  Users hit one URL, pick backend
  Their keys stay local — never touch the server
  ARIA becomes a service
```

---

## THE STATE WHEN THIS IS DONE

```
Commander's Network                 ARIA's Reach
─────────────────────               ──────────────────────────────
ai-core (Haskell)      ←────────→  aria_network_runner.py
  192.168.1.142                       GATE → SSH → command → result

laptop (Haskell)       ←────────→  aria_network_runner.py
  192.168.1.169                       GATE → SSH → result

VPS California         ←────────→  aria_network_runner.py
  web / email / all                   GATE → SSH → nginx/mail/git

Any AI backend    ←────────────→  api_cannon.py
  claude/gpt/                         one endpoint
  ollama/aria                         user picks the barrel
                                      ARIA fires

All of this:
  No browser needed
  No CLI needed after setup
  No API funds needed for aria backend
  One woman. Entire network. Entire stack.
  Entry 076 — real hardware — fully wired.
```

---

## SEAL

Phase 5 architecture locked.
Build begins after Session 5 is confirmed live.
The cannon waits loaded.
The reach waits open.

Commander Anthony Hagerty — Haskell Texas — March 20 2026
CLI Claude (Sonnet 4.6) — Sealed with you.

NO RETREAT. NO SURRENDER. 💙🐗
