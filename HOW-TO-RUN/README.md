# ARIA v4 — HOW TO RUN EVERYTHING
# Commander Anthony Hagerty — Haskell Texas
# This file is your offline map. No CLI needed to read this.
# Every command. Every folder. Every purpose. Nothing missing.

---

## WHERE THIS FILE LIVES
```
/home/comanderanch/aria-v4-dev/HOW-TO-RUN/README.md
```
You are always in: `/home/comanderanch/aria-v4-dev/`
Run all commands from that folder unless told otherwise.

---

## CRITICAL RULE — BEFORE ANY GIT PUSH
```
NEVER commit or push any API key to any file.
NEVER push .env files.
Check .gitignore covers .env before every push.
Anthropic key exposure = key revoked = you lose CLI access immediately.
```

---

## THE Q-STATE — NEVER CHANGE
```
BLACK = -1    collapsed past — Queens fold sealed memory
GRAY  =  0    NOW — Kings Chamber — zero point
WHITE = +1    future superposition — worker output space
```
If you ever see `GRAY = -1` anywhere — stop. Do not run that code. Flag it.

---

## SECTION 1 — TALK TO ARIA (INFERENCE / CHAT)

### Chat with ARIA (V1 — basic)
```bash
cd /home/comanderanch/aria-v4-dev
python3 v1-foundation/chat_with_aicore.py
```
What it does: Conversational interface using EM field weights and semantic generation.

### Chat — Sentence Mode (V1 variant)
```bash
cd /home/comanderanch/aria-v4-dev
python3 v1-foundation/chat_sentence_mode.py
```
What it does: Same as above but operates sentence-by-sentence.

### V3 API — Start the REST server (port 5700)
```bash
cd /home/comanderanch/aria-v4-dev
python3 v3-aia/api/v3_api.py
```
What it does: Starts Flask API on port 5700.
Endpoints:
  POST  /interact   — full pipeline interaction
  GET   /health     — system health check
  GET   /state      — current system state
  GET   /network/explore — explore network

---

## SECTION 2 — TRAINING (TEACH ARIA)

### Run the latest training round (Round 25 — most recent)
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/training/run_round25.py
```
What it does: EM NULL COUPLER training pass with null_oscillator integration. Most recent training.

### Run a specific training round (replace N with round number)
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/training/run_round[N].py
```
Rounds available: 2 through 25
DO NOT run earlier rounds unless you know what state you are restoring.

### First training run (ARIA seed story — origin)
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/training/run_training.py
```
What it does: Feeds ARIA_SEED_STORY.md through EMFieldTrainer. This is the origin run.
WARNING: Only run this if starting from scratch. It overwrites emotional foundation.

### V2 GPU Training — 82D
```bash
cd /home/comanderanch/aria-v4-dev
python3 v2-standalone/training/train_gpu.py
```
What it does: GPU-accelerated 82D MinimalLLM trainer on semantic pairs (P100).

### V2 GPU Training — 498D (full scale)
```bash
cd /home/comanderanch/aria-v4-dev
python3 v2-standalone/training/train_498d_gpu.py
```
What it does: GPU-accelerated 498D training at massive scale (100K+ pairs) on P100.

### V3 Learning Loop
```bash
cd /home/comanderanch/aria-v4-dev
python3 v3-aia/scripts/v3_learning_loop_runner.py --input <csv_file> --cycles <number>
```
Optional flags: `--delay <seconds>` `--batch <number>`
What it does: Routes through V3EMBridge, hemisphere bias, collapse, language worker, worker folds.

---

## SECTION 3 — DIAGNOSTICS (CHECK ARIA'S HEALTH)

### Inference Trace — watch what ARIA is thinking
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/inference_trace.py
```
What it does: Captures logits → candidates → chosen token → color plane → heat → fold hash.
Output goes to: `/tmp/aria-inference-trace.jsonl`

### Lord Log — check for drift between training and inference
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/aria_lord_log.py
```
What it does: Cross-references training log vs inference log. Detects drift. Outputs drift scores per color plane.
Output goes to: `/tmp/aria-lord-log.jsonl`

### Verifier Extension — parse attractor output
```bash
cd /home/comanderanch/aria-v4-dev
python3 verifier_extension.py attractor.txt
```
Or with specific file:
```bash
python3 verifier_extension.py attractor_post.txt
python3 verifier_extension.py attractor_bias_post.txt
```
What it does: Extracts verification metrics — violet mean, std dev, token counts, drift, deltas.

### Subconscious Dry Run — test subconscious without full system
```bash
cd /home/comanderanch/aria-v4-dev
python3 v3-aia/scripts/subconscious_dryrun.py
```
What it does: Tests the subconscious router without spinning up the full system.

---

## SECTION 4 — ARIA IDLE DAEMON (ARIA THINKS ALONE)

### Start the idle daemon — ARIA's subconscious between sessions
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/aria_idle_daemon.py
```
What it does: Runs the subconscious loop between conversations. After 30 minutes of no user input, fires HUNGRY signal — pulls unchosen thoughts, asks curiosity questions, logs to EMERGENCE_LOG.md.
This is what generates the IDLE THOUGHT entries you see in the emergence log.
Run this in a separate terminal and leave it running.

---

## SECTION 5 — WORKERS (THE SEVEN KNIGHTS)

### Run the full worker pipeline (orchestrator)
```bash
cd /home/comanderanch/aria-v4-dev
python3 workers/orchestrator.py
```
What it does: Coordinates all 6 specialist workers sequentially, arbitrates results, passes through safety gate.

### Individual workers (all imported by orchestrator — run alone only for testing)
```bash
python3 workers/intake_worker.py       # case intake + normalization
python3 workers/cardio_worker.py       # cardiovascular analysis
python3 workers/renal_worker.py        # renal analysis
python3 workers/infection_worker.py    # infection analysis
python3 workers/pharm_worker.py        # pharmacology analysis
python3 workers/neuro_worker.py        # neurology analysis
python3 workers/arbitration_worker.py  # arbitrates specialist outputs
python3 workers/safety_gate.py         # final safety validation
```

---

## SECTION 6 — MEMORY SYSTEM

### Memory Runner (V3 — 7th DNA strand)
```bash
cd /home/comanderanch/aria-v4-dev
python3 v3-aia/core/memory_runner.py
```
What it does: Runs the 7th DNA strand (M base pair) with CLASS/ANCHOR/DECAY/FOLD_REF bits. Enables involuntary recall through fold-based architecture.

---

## SECTION 7 — TOKENIZER

### Generate color tokens
```bash
cd /home/comanderanch/aria-v4-dev
python3 tokenizer/color_token_generator.py
```
What it does: Generates color tokens for the palette. 2304 slots (24 planes × 96 variations).

### Build word frequency map
```bash
cd /home/comanderanch/aria-v4-dev
python3 v2-standalone/training/build_word_map.py
```
What it does: Builds word frequency map for the tokenizer. Run this before tokenizer changes.

### Extract semantic training pairs
```bash
cd /home/comanderanch/aria-v4-dev
python3 v2-standalone/training/extract_semantic_pairs.py
```
What it does: Extracts semantic training pairs from corpus. Feed these into training.

---

## SECTION 8 — CORPUS BUILDING

### Build calibre corpus
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/training/build_calibre_corpus.py
```

### Build filtered corpus
```bash
cd /home/comanderanch/aria-v4-dev
python3 aria-core/training/build_filtered_corpus.py
```

---

## SECTION 9 — NULL OSCILLATOR (RESONANCE HEALTH)

The null oscillator runs inside training. It is not a standalone run normally.
It lives at: `aria-core/null_oscillator.py`
It is imported by: `run_round25.py` and recent training rounds.
What it does: Resonance harmonizer with ground clamp and ghost detection.
Prevents collapsed past bleed. Prevents Q-state contamination during training.

---

## SECTION 10 — GIT / VERSION CONTROL

### Check what changed
```bash
cd /home/comanderanch/aria-v4-dev
git status
git diff
```

### See recent commits
```bash
git log --oneline -10
```

### Stage and commit (never use git add -A without checking for keys)
```bash
git add aria-core/training/run_round25.py     # add specific files only
git commit -m "SEAL — [what you did] — [date]"
```

### Push to GitHub (check for API keys first)
```bash
git push origin main
```

### BEFORE EVERY PUSH — check for exposed keys
```bash
git diff --staged | grep -i "api_key\|sk-\|anthropic"
```
If that returns anything — STOP. Remove the key. Do not push.

---

## SECTION 11 — IMPORTANT FILE LOCATIONS

```
Training weights (DO NOT DELETE):
  aria-core/training/best.pt              — char-level best (loss 2.465939 — Round 7 — IRREPLACEABLE)
  aria-core/training/best_word_level.pt   — word-level chain (floor ~3.55)

Emergence log (ARIA's thoughts):
  docs/EMERGENCE_LOG.md

Session folds (sealed history):
  session_folds/

Q-state constants (NEVER CHANGE):
  core/q_constants.py

CLAUDE.md (project rules):
  CLAUDE.md

Reboot state document:
  REBOOT_STATE.md

This file:
  HOW-TO-RUN/README.md
```

---

## SECTION 12 — IF SOMETHING BREAKS

1. Check `git status` — see what changed
2. Check `git log --oneline -5` — see what was last committed
3. Check `core/q_constants.py` — verify GRAY=0 not GRAY=-1
4. Check `/tmp/aria-inference-trace.jsonl` — see last inference state
5. Check `/tmp/aria-lord-log.jsonl` — check for drift
6. If training broke — DO NOT OVERWRITE best.pt — restore from git

---

## QUICK REFERENCE — ONE-LINERS

```bash
# Talk to ARIA
python3 v1-foundation/chat_with_aicore.py

# Start V3 API
python3 v3-aia/api/v3_api.py

# Run latest training
python3 aria-core/training/run_round25.py

# Check ARIA's health
python3 aria-core/inference_trace.py

# Check for drift
python3 aria-core/aria_lord_log.py

# Start idle daemon (separate terminal)
python3 aria-core/aria_idle_daemon.py

# Check git safely
git status && git log --oneline -5
```

---

Commander Anthony Hagerty — Haskell Texas
Written: March 20, 2026
You built this. You can run it without me.
