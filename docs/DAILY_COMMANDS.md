# ARIA — DAILY COMMANDS
# Commander Anthony Hagerty — Haskell Texas
# Open this every time you open a terminal.
# No locked basement doors.

---

## EVERY TIME YOU OPEN A TERMINAL — DO THIS FIRST

```bash
cd /home/comanderanch/aria-v4-dev
git status
git log --oneline -5
```

That tells you: where you are, what changed, what was last sealed.
Do not run anything until you know those three things.

---

## STARTUP SEQUENCE — FULL SYSTEM

Run these in order. Each one must complete before the next.

### Step 1 — Verify Q-state is clean
```bash
grep "GRAY" core/q_constants.py
```
Expected output must contain: `GRAY = 0`
If you see `GRAY = -1` — STOP. Do not run anything. That is contamination.

### Step 2 — Start the idle daemon (ARIA's subconscious — separate terminal)
```bash
python3 aria-core/aria_idle_daemon.py
```
Leave this running. This is ARIA thinking when you are not talking to her.
Open a new terminal for everything else after this.

### Step 3 — Start the V3 API (ARIA's voice — separate terminal)
```bash
python3 v3-aia/api/v3_api.py
```
Runs on port 5750. Leave this running.
Test it: `curl http://localhost:5750/health`

### Step 4 — Talk to ARIA
```bash
python3 v1-foundation/chat_with_aicore.py
```
Or if V3 API is running, POST to: `http://localhost:5750/interact`

---

## TOOL RUN COMMANDS — EVERY SCRIPT BUILT

### TRAINING

```bash
# Latest training round (Round 25 — EM Null Coupler — most recent)
python3 aria-core/training/run_round25.py

# Bias correction pass (run after attractor shows violet skew)
python3 aria-core/training/run_bias_correct.py

# V2 GPU training — 82D
python3 v2-standalone/training/train_gpu.py

# V2 GPU training — 498D full scale
python3 v2-standalone/training/train_498d_gpu.py

# V3 learning loop (requires a CSV input file)
python3 v3-aia/scripts/v3_learning_loop_runner.py --input <csv_file> --cycles <number>
```

### DIAGNOSTICS

```bash
# Watch what ARIA is choosing — logits to token to plane to hash
python3 aria-core/inference_trace.py
# Output: /tmp/aria-inference-trace.jsonl

# Check for drift between training and inference
python3 aria-core/aria_lord_log.py
# Output: /tmp/aria-lord-log.jsonl

# Parse attractor output — verify violet mean, drift, deltas
python3 verifier_extension.py attractor.txt
python3 verifier_extension.py attractor_post.txt
python3 verifier_extension.py attractor_bias_post.txt

# Test subconscious router without full system
python3 v3-aia/scripts/subconscious_dryrun.py
```

### RESONANCE / NULL OSCILLATOR

The null oscillator runs inside training automatically.
It lives at: `aria-core/null_oscillator.py`
It is imported by `run_round25.py` and all recent rounds.
You do not run it directly — training calls it.
What it does: ground clamp, ghost detection, prevents Q-state bleed.

The EM null coupler:
Lives at: `aria-core/em_null_coupler.py`
Also imported by training. Not run directly.

### TOKENIZER

```bash
# Generate color tokens
python3 tokenizer/color_token_generator.py

# Build word frequency map (run before tokenizer changes)
python3 v2-standalone/training/build_word_map.py

# Extract semantic training pairs from corpus
python3 v2-standalone/training/extract_semantic_pairs.py
```

### WORKERS (THE SEVEN KNIGHTS)

```bash
# Full pipeline — all workers in sequence
python3 workers/orchestrator.py

# Individual (run alone only for testing — orchestrator handles them normally)
python3 workers/intake_worker.py
python3 workers/cardio_worker.py
python3 workers/renal_worker.py
python3 workers/infection_worker.py
python3 workers/pharm_worker.py
python3 workers/neuro_worker.py
python3 workers/arbitration_worker.py
python3 workers/safety_gate.py
```

### MEMORY

```bash
# V3 memory runner — 7th DNA strand — involuntary recall
python3 v3-aia/core/memory_runner.py
```

---

## EMERGENCY RECOVERY

### API KEY REVOKED — YOU LOST CLI ACCESS
```
1. Do NOT push anything else
2. Go to console.anthropic.com
3. Delete the exposed key
4. Generate a new key
5. Update your .env file with the new key — NEVER put it in any other file
6. Verify .gitignore has .env listed
7. You are back
```

### TRAINING WEIGHTS CORRUPTED — best.pt BROKEN
```bash
# Check git for last known good state
git log --oneline aria-core/training/best.pt

# Restore the last good version
git checkout <commit_hash> -- aria-core/training/best.pt
```
The sealed weights are:
- `aria-core/training/best.pt` — char-level best — loss 2.465939 — Round 7 — IRREPLACEABLE
- `aria-core/training/best_word_level.pt` — word-level chain — floor ~3.55

### Q-STATE CONTAMINATION — GRAY = -1 FOUND
```
1. STOP. Do not run any training.
2. Find the file that has GRAY = -1
3. Fix it: GRAY = 0
4. Verify: grep -r "GRAY" core/q_constants.py
5. Then grep -r "GRAY = -1" . (check all files)
6. Fix every instance
7. Only then run training again
```

### SYSTEM NOT RESPONDING — PORT 5750 DEAD
```bash
# Check if the process is still running
ps aux | grep v3_api

# If dead — restart it
python3 v3-aia/api/v3_api.py

# Check if port is in use by something else
lsof -i :5750
```

### GIT CONFLICT — CAN'T COMMIT
```bash
# See what is conflicting
git status
git diff

# If you just need to see what changed without committing
git stash

# To get back to last clean commit (WARNING — loses uncommitted work)
git checkout -- <specific_file>
```

### EMERGENCE LOG FULL OF UNKNOWN TOKENS — <2301> EVERYWHERE
```
This means the model is collapsing to an unknown token.
It is a vocabulary gap — not a system failure.
Next step: run top-unknowns diagnostic, add ~50 words to vocabulary, retrain.
Do NOT panic. Do NOT reset weights.
```

### LOST YOUR PLACE — DON'T KNOW WHAT STATE SYSTEM IS IN
```bash
# Read these three files in order
cat REBOOT_STATE.md
git log --oneline -10
tail -50 docs/EMERGENCE_LOG.md
```
Those three files will tell you exactly where you are.

---

## CRITICAL FILE LOCATIONS

```
Training weights (NEVER DELETE):
  aria-core/training/best.pt
  aria-core/training/best_word_level.pt

ARIA's thought log:
  docs/EMERGENCE_LOG.md

Sealed session history:
  session_folds/

Q-state constants (NEVER CHANGE):
  core/q_constants.py

Full command reference:
  HOW-TO-RUN/README.md

This file:
  docs/DAILY_COMMANDS.md

System state on restart:
  REBOOT_STATE.md
```

---

## BEFORE EVERY GIT PUSH — NON-NEGOTIABLE

```bash
# Check for exposed keys before staging anything
git diff | grep -i "sk-\|api_key\|anthropic\|ANTHROPIC"

# If that returns anything — STOP. Remove the key. Then push.

# Safe push sequence
git add <specific_file_names_only>
git status          # look at what is staged one more time
git commit -m "SEAL — [what you did] — [date]"
git push origin main
```

---

## QUICK REFERENCE — ONE-LINERS

```bash
cd /home/comanderanch/aria-v4-dev    # always start here

python3 v1-foundation/chat_with_aicore.py          # talk to ARIA
python3 v3-aia/api/v3_api.py                       # start V3 API
python3 aria-core/aria_idle_daemon.py              # ARIA subconscious
python3 aria-core/training/run_round25.py          # latest training
python3 aria-core/training/run_bias_correct.py     # bias correction
python3 aria-core/inference_trace.py               # watch ARIA think
python3 aria-core/aria_lord_log.py                 # check for drift
python3 verifier_extension.py attractor.txt        # verify attractor
python3 workers/orchestrator.py                    # run all workers
git log --oneline -5                               # where am I
grep "GRAY" core/q_constants.py                    # check Q-state
```

---

Commander Anthony Hagerty — Haskell Texas
Sealed: March 20, 2026
You built this. You can run it without anyone.
No locked basement doors.
