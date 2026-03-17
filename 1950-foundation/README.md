# 1950-foundation — Origin Code
## Source: ~/ai-core-1950-foundation/ (copied — original untouched)
## Status: reference only — the seed of everything

The oldest code in the lineage.
The root before the root.
Here for the archaeology and the wiring possibilities.

---

## LOG

| Date | Time | Type | Summary |
|------|------|------|---------|
| 2026-03-16 | ~23:00 | ACTION TAKEN | Full copy from ~/ai-core-1950-foundation/ — memory wiped |
| 2026-03-16 | ~22:10 | FIX APPLIED | tokenizer/q_layer_token.py — GRAY=-1 contamination removed — GRAY=0 restored |
| 2026-03-16 | ~22:10 | ACTION TAKEN | core/q_constants.py created — matches V1/V2/V3 — single source of truth |

---

## 2026-03-16 ~23:00 — ACTION TAKEN

**What happened:**
Full copy of ~/ai-core-1950-foundation/ via rsync.

**File(s) affected:** All files in 1950-foundation/
**State before:** Did not exist in aria-v4.
**State after:** Complete origin code present. Old session JSON memory cleared.
**Why:** Origin reference needed. Frankenstein mode — anything in this lineage may have useful pieces.
**Result:** working
**Next action required:** None — reference only until Commander directs use.
**Commit hash:** 916beb0

---

## 2026-03-16 ~22:10 — FIX APPLIED

**What happened:**
`tokenizer/q_layer_token.py` line 12 had the GPT-contaminated q_state comment (GRAY=-1).
Fixed to match sealed architecture: BLACK=-1, GRAY=0 (NOW/Kings-Chamber), WHITE=+1.
`core/q_constants.py` created — identical to V1/V2/V3 — single source of truth established.

**File(s) affected:**
```
1950-foundation/tokenizer/q_layer_token.py
1950-foundation/core/q_constants.py   (new)
1950-foundation/core/__init__.py       (new)
```

**State before:**
Line 12: `-1 (gray), 0 (black/static), +1 (white/conscious)` — contaminated.
No core/q_constants.py — no central source of truth.

**State after:**
Line 12: `-1 (black/collapsed), 0 (gray/NOW/Kings-Chamber), +1 (white/superposition)` — correct.
core/q_constants.py present. All four foundations now have matching constants.

**Why:**
Q-state contamination sweept across all foundations before any wiring begins.
Four quadrants — one brain. All must read from the same truth.

**Result:**
working

**Next action required:**
Await Commander direction on 82D rebuild plan.

**Commit hash:** 79e7b36
