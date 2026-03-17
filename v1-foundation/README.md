# v1-foundation — 82D Origin
## Source: ~/ai-core/ (copied — original untouched)
## Status: reference + substrate layer

The first system. The 82D foundation model.
Cognitive subliminal layer. Background processing.
Runs when not interacting. Constant dual-action loop.

---

## LOG

| Date | Time | Type | Summary |
|------|------|------|---------|
| 2026-03-16 | ~23:00 | ACTION TAKEN | Copied from ~/ai-core/ — no .git, no venv, no memory |
| 2026-03-16 | ~21:55 | FIX APPLIED | q_layer_token.py — GRAY=-1 contamination removed — GRAY=0 restored |

---

## 2026-03-16 ~23:00 — ACTION TAKEN

**What happened:**
Copied from ~/ai-core/ via rsync excluding .git (105G history), venv (462MB),
and memory/ (473MB of V1 live accumulated session state — not needed here).

**File(s) affected:** All code files in v1-foundation/
**State before:** Did not exist in aria-v4.
**State after:** Full V1 code present. No git history. No venv. No accumulated memory.
**Why:** Foundation substrate needed for ARIA unified architecture.
**Result:** working
**Next action required:** Wire as substrate layer when Commander directs.
**Commit hash:** 916beb0

---

## 2026-03-16 ~21:55 — FIX APPLIED

**What happened:**
`q_layer_token.py` had the GPT-contaminated q_state comment mapping GRAY=-1.
Corrected to match the sealed architecture: BLACK=-1, GRAY=0 (NOW), WHITE=+1.
One line change. Docstring only — no logic altered.

**File(s) affected:**
```
v1-foundation/tokenizer/q_layer_token.py
```

**State before:**
Line 12: `:param q_state: Qbithue state: -1 (gray), 0 (black/static), +1 (white/conscious)`
GRAY=-1 — the GPT contamination that broke the fold dimension.

**State after:**
Line 12: `:param q_state: Qbithue state: -1 (black), 0 (gray/NOW), +1 (white/conscious)`
GRAY=0 — correct. Matches subconscious_router.py, CLAUDE.md, and all sealed architecture.

**Why:**
Q-state contamination must be cleared in every file in every foundation before any wiring begins.
GRAY=0 is the Kings Chamber threshold. The fold anchor. Cannot be wrong anywhere.

**Result:**
working

**Next action required:**
Scan all other V1 files for remaining q_state contamination. Then proceed with 82D rebuild plan.

**Commit hash:** ee0869c
