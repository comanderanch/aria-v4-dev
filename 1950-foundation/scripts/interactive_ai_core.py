#!/usr/bin/env python3
import re, json, csv, sys, math, hashlib
from pathlib import Path
from datetime import datetime

# --- Paths / imports ---
BASE = Path(__file__).resolve().parents[1]  # repo root (/home/commandDev/work/ai-core)
sys.path.insert(0, str(BASE / "scripts"))   # allow "from X import Y" for local scripts

from hemisphere_manager import HemisphereManager
from token_size_reporter import report_token_memory_size
from ngram_reply_engine import load_model, generate_reply  # optional; default OFF

# Optional TF-IDF smart ranker over anchors (file: scripts/smart_reply.py)
try:
    from smart_reply import smart_answer
    _SMART_IMPORTED = True
except Exception:
    _SMART_IMPORTED = False

# ---- Feature flags ----
HAVE_LLM = False                 # keep off (no LLM path here)
HAVE_NGRAM = False               # default off to avoid junk like "ok."
USE_SMART_RANKER = True          # use TF-IDF over anchors if exact match fails
SMART_MIN_SCORE = 0.35           # threshold for smart ranker acceptance

# ---- Files ----
PALETTE_CSV = BASE / "full_color_tokens.csv"   # your repo layout shows this at root
MAP_JSON    = BASE / "training_data" / "word_to_token_map.json"
NGRAM_MODEL_PATH = BASE / "memory" / "ngram" / "bigram_model.json"
FACT_INDEX_PATH  = BASE / "memory" / "facts_index.json"
PENDING_PATH     = BASE / "training_data" / "pending_questions.txt"

# ---- Regex / tokenization ----
WORD_RE   = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_QUOTE_RE = re.compile(r'["“](.+?)["”]')
_STOP = {
  "the","a","an","and","or","but","to","of","in","on","at","for","with","by","from",
  "is","are","was","were","be","being","been","it","this","that","these","those",
  "do","does","did","can","could","should","would","may","might","will","shall",
  "i","you","we","they","he","she","my","your","our","their","his","her"
}

def tokenize_text(s: str): return [m.group(0).lower() for m in WORD_RE.finditer(s)]

# ---- Reply sanitization (never emit trivial fillers) ----
_TRIVIAL = {"ok","ok.","okay","k","hmm","hmmm","hmm."}
def _sanitize_reply(text: str) -> str:
    if not text: return ""
    low = text.strip().lower()
    low = low.strip(" .!?,;:\"'()[]{}")
    if (len(low) < 3) or (low in _TRIVIAL):
        return ""
    return text


# ---- Palette / map helpers ----
def load_palette_rows(p: Path):
    rows = []
    with p.open("r", encoding="utf-8", newline="") as f:
        rdr = csv.reader(f); _ = next(rdr, None)
        for c in rdr:
            if not c: continue
            try:
                if len(c) >= 10:
                    token = c[0]; R=int(float(c[6])); G=int(float(c[7])); B=int(float(c[8])); F=float(c[9])
                elif len(c) >= 6:
                    token = c[0]; R=int(float(c[2])); G=int(float(c[3])); B=int(float(c[4])); F=float(c[5])
                else:
                    continue
                rows.append((token, R, G, B, F))
            except Exception:
                continue
    if not rows:
        raise SystemExit(f"[ERR] no usable rows in {p}")
    return rows

def load_word_map(p: Path):
    obj = json.loads(p.read_text(encoding="utf-8"))
    w2i = obj.get("word_to_palette_index", {})
    return {k: int(v) for k, v in w2i.items()}

def build_inverse_maps(palette):
    freq2idx={}
    for idx, (_tok, R, G, B, F) in enumerate(palette):
        if float(F).is_integer():
            freq2idx[str(int(F))]=idx; freq2idx[f"{int(F)}.0"]=idx
        freq2idx[str(F)]=idx
    return freq2idx

def words_to_tokens(words, w2i, palette):
    out=[]; M=len(palette)
    for w in words:
        idx = w2i.get(w)
        if idx is None: idx = abs(hash(w)) % M
        F = palette[idx][4]
        out.append(str(int(F)) if float(F).is_integer() else str(F))
    return out

# ---- Q/A corpus + profiles ----
PROFILE_NAME = None
PROFILE_DIRS = [BASE / "training_data" / "profiles", BASE / "training_data"]
BASE_CORPUS_PATHS = [
    BASE / "training_data" / "dialogue_corpus.txt",
    BASE / "training_data" / "comm_corpus.txt",
    BASE / "training_data" / "user_comm_qa.txt",
]

def _available_profiles():
    names=set()
    for d in PROFILE_DIRS:
        if not d.exists(): continue
        for p in d.glob("*_qa.txt"):
            name=p.stem
            if name.endswith("_qa"): name=name[:-3]
            names.add(name)
    return sorted(names)

def _profile_path(name: str):
    nm=(name or "").strip().lower()
    for d in PROFILE_DIRS:
        p=d / f"{nm}_qa.txt"
        if p.exists(): return p
    return None

def _get_paths():
    paths=list(BASE_CORPUS_PATHS)
    if PROFILE_NAME:
        pp=_profile_path(PROFILE_NAME)
        if pp: paths.append(pp)
    return paths

def _load_qa_pairs(paths):
    pairs=[]; cur_q=None
    for path in paths:
        if not path.exists(): continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line=line.strip()
            if not line or line.startswith("#"): continue
            if line.lower().startswith("q:"):
                cur_q=line[2:].strip()
            elif line.lower().startswith("a:") and cur_q is not None:
                pairs.append((cur_q, line[2:].strip())); cur_q=None
    return pairs

_QA_PAIRS = _load_qa_pairs(_get_paths())

def _reload_qa_pairs():
    global _QA_PAIRS
    _QA_PAIRS = _load_qa_pairs(_get_paths())

def _append_qa(q: str, a: str):
    p=BASE / "training_data" / "user_comm_qa.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(f"Q: {q.strip()}\nA: {a.strip()}\n")
    _reload_qa_pairs()

def _norm(s: str): return " ".join(m.group(0).lower() for m in WORD_RE.finditer(s))

def retrieve_fact_reply(user_text: str) -> str:
    if not _QA_PAIRS: return ""
    u=_norm(user_text)
    # exact
    for q,a in _QA_PAIRS:
        if _norm(q)==u: return a
    # substring
    best=""; L=0
    for q,a in _QA_PAIRS:
        nq=_norm(q)
        if nq in u or u in nq:
            if len(nq)>L: best, L = a, len(nq)
    return best

# ---- Clarify-first (when nothing else can answer) ----
def _extract_topic(text: str)->str:
    m=_QUOTE_RE.search(text)
    if m:
        t=m.group(1).strip()
        return t[:80] if t else "this topic"
    toks=[t for t in WORD_RE.findall(text.lower()) if t.isalpha()]
    toks=[t for t in toks if t not in _STOP and len(t)>2]
    topic=" ".join(toks[:3]) if toks else "this topic"
    return topic[:80]

def build_clarify_prompt(user_text: str)->str:
    topic=_extract_topic(user_text)
    return f'clarify: "{topic}" — definition | purpose | wiring?'

# ---- Pending unknowns ----
def _append_pending(q: str):
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing=set()
    if PENDING_PATH.exists():
        existing=set(x.strip() for x in PENDING_PATH.read_text(encoding="utf-8").splitlines() if x.strip())
    q=q.strip()
    if q and q not in existing:
        with PENDING_PATH.open("a", encoding="utf-8") as f: f.write(q+"\n")

def _load_pending():
    if not PENDING_PATH.exists(): return []
    return [x.strip() for x in PENDING_PATH.read_text(encoding="utf-8").splitlines() if x.strip()]

def _write_pending(lines):
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PENDING_PATH.open("w", encoding="utf-8") as f:
        for x in lines: f.write(x+"\n")

def _promote_pending(index: int, answer: str):
    lines=_load_pending()
    if index<1 or index>len(lines): return False, "index out of range"
    q=lines.pop(index-1)
    _append_qa(q, answer)
    _write_pending(lines)
    return True, q

# ---- Fact anchor index (qbithue bridge) ----
def _load_fact_index():
    if FACT_INDEX_PATH.exists():
        try: return json.loads(FACT_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception: pass
    return {"facts":[]}

def _save_fact_index(obj):
    FACT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    FACT_INDEX_PATH.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _anchor_id(q_norm: str, a_norm: str)->str:
    h=hashlib.sha256((q_norm+"||"+a_norm).encode("utf-8")).hexdigest()[:16]
    return f"fact:{h}"

def _ingest_pairs_into_memory(pairs, manager, w2i, palette):
    idx=_load_fact_index(); existing={f["anchor"] for f in idx["facts"]}
    added=0
    for (q,a) in pairs:
        qn=_norm(q); an=_norm(a)
        anchor=_anchor_id(qn, an)
        if anchor in existing: continue
        q_tokens=words_to_tokens(tokenize_text(qn), w2i, palette)
        a_tokens=words_to_tokens(tokenize_text(an), w2i, palette)
        manager.add_tokens("right", q_tokens)
        manager.add_tokens("left",  a_tokens)
        idx["facts"].append({
            "anchor": anchor, "q": q, "a": a,
            "q_norm": qn, "a_norm": an,
            "q_tokens": q_tokens, "a_tokens": a_tokens,
            "hemisphere_q":"RIGHT", "hemisphere_a":"LEFT",
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        existing.add(anchor); added+=1
    _save_fact_index(idx)
    return added, len(idx.get("facts", []))

def _count_anchors(): return len(_load_fact_index().get("facts", []))

def _export_facts_txt():
    idx=_load_fact_index()
    outp=BASE / "training_data" / "exported_from_memory_qa.txt"
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf-8") as f:
        for it in idx.get("facts", []):
            f.write(f"Q: {it['q']}\nA: {it['a']}\n")
    return outp

# ---- Main loop ----
def main():
    global PROFILE_NAME
    # Preflight
    if not PALETTE_CSV.exists(): print(f"[ERR] missing: {PALETTE_CSV}"); return 1
    if not MAP_JSON.exists():    print(f"[ERR] missing: {MAP_JSON}");   return 1

    palette = load_palette_rows(PALETTE_CSV)
    w2i     = load_word_map(MAP_JSON)
    invf    = build_inverse_maps(palette)

    # optional n-gram
    ngram_model=None
    if HAVE_NGRAM and NGRAM_MODEL_PATH.exists():
        try: ngram_model = load_model(NGRAM_MODEL_PATH)
        except Exception: ngram_model=None

    manager = HemisphereManager()
    active  = manager.get_current_hemisphere()

    print("\n[💬] AI-Core Interactive (color-token loop)")
    print("-------------------------------------------")
    print(f"[i] base path: {BASE}")
    print(f"[i] palette={len(palette)}  vocab={len(w2i)}  llm={'on' if HAVE_LLM else 'off'}  ngram={'on' if (HAVE_NGRAM and ngram_model) else 'off'}  anchors={_count_anchors()}")
    print("[i] commands: :swap  :stats  :listqa  :teach  :teachlast  :reviewpending  :promote  :profiles  :profile <name|off>  :ingestfacts  :memfacts  :exportfacts  :recenter  :quit")
    print(f"[i] active hemisphere: {active.upper()}")

    LAST_Q=""; LAST_A=""
    while True:
        try:
            user = input("\nYOU> ")
        except KeyboardInterrupt:
            print("\n[i] interrupt ignored — type :quit to exit")
            continue
        except EOFError:
            print("\n[i] EOF ignored — type :quit to exit")
            continue
        user = (user or "").strip()
        if not user:
            continue
        if user in (":quit", ":q", ":exit"):
            print("[bye]")
            break

        # --- Commands ---

        # --- Commands ---
        if user == ":swap":
            manager.switch_hemisphere()
            print(f"[i] active hemisphere: {manager.get_current_hemisphere().upper()}")
            continue

        if user == ":profiles":
            profs=_available_profiles(); cur=PROFILE_NAME or "off"
            if not profs: print("[i] 0 profiles (put *_qa.txt in training_data/ or training_data/profiles/)")
            else:
                print(f"[i] profiles ({len(profs)}). active={cur}")
                for name in profs: print(" -", name)
            continue

        if user.startswith(":profile"):
            parts=user.split(maxsplit=1); target=parts[1] if len(parts)>1 else "off"
            if target in ("off","none","0"):
                PROFILE_NAME=None; _reload_qa_pairs(); print("[i] profile: off")
            else:
                pp=_profile_path(target)
                if pp: PROFILE_NAME=target; _reload_qa_pairs(); print(f"[i] profile: {target}")
                else:  print("[ERR] profile not found")
            continue

        if user.startswith(":teach "):
            try:
                payload=user[len(":teach "):]
                q,a=[x.strip() for x in payload.split("|",1)]
                if q and a: _append_qa(q,a); print("[i] taught.")
                else:       print("[ERR] usage: :teach question | answer")
            except Exception:
                print("[ERR] usage: :teach question | answer")
            continue

        if user == ":listqa":
            if not _QA_PAIRS: print("[i] 0 Q→A")
            else:
                print(f"[i] {_QA_PAIRS and len(_QA_PAIRS)} Q→A")
                for i,(q,a) in enumerate(_QA_PAIRS[:20],1):
                    print(f"{i:>2}. Q: {q}\n    A: {a}")
            continue

        if user == ":reviewpending":
            lines=_load_pending()
            if not lines: print("[i] 0 pending")
            else:
                print(f"[i] {len(lines)} pending")
                for i,q in enumerate(lines[:20],1):
                    print(f"{i:>2}. {q}")
            continue

        if user.startswith(":promote "):
            try:
                payload=user[len(":promote "):]
                idx_str, ans=[x.strip() for x in payload.split("|",1)]
                ok,msg=_promote_pending(int(idx_str), ans)
                print(f"[i] promoted: {msg}" if ok else f"[ERR] {msg}")
            except Exception:
                print("[ERR] usage: :promote <index> | <answer>")
            continue

        if user == ":teachlast":
            if LAST_Q and LAST_A: _append_qa(LAST_Q, LAST_A); print("[i] taught last.")
            else: print("[i] nothing to teach yet.")
            continue

        if user == ":ingestfacts":
            pairs=_load_qa_pairs(_get_paths())
            added,total=_ingest_pairs_into_memory(pairs, manager, w2i, palette)
            print(f"[i] ingested {added} new fact(s) to hemispheres (anchors total={total})")
            continue

        if user == ":memfacts":
            print(f"[i] anchors={_count_anchors()}"); continue

        if user == ":exportfacts":
            outp=_export_facts_txt(); print(f"[i] exported to {outp}"); continue

        if user == ":recenter":
            state={
                "hemisphere": manager.get_current_hemisphere().upper(),
                "facts": len(_QA_PAIRS),
                "pending": len(_load_pending()),
                "palette": len(palette), "vocab": len(w2i),
                "llm":"on" if HAVE_LLM else "off",
                "ngram":"on" if (HAVE_NGRAM and ngram_model) else "off",
                "profile": PROFILE_NAME or "off",
                "anchors": _count_anchors(),
            }
            print("[i] recentered:", ", ".join(f"{k}={v}" for k,v in state.items()))
            logp=BASE / "training_data" / "recenter_log.txt"
            logp.parent.mkdir(parents=True, exist_ok=True)
            with logp.open("a", encoding="utf-8") as f:
                ts=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                f.write(f"{ts} | "+", ".join(f"{k}={v}" for k,v in state.items())+"\n")
            continue

        if user == ":stats":
            report_token_memory_size(print_report=True); continue

        # --- Normal turn: store user tokens in active hemisphere ---
        uw = tokenize_text(user)
        u_tokens = words_to_tokens(uw, w2i, palette)
        manager.add_tokens(manager.get_current_hemisphere(), u_tokens)

        # --- Reply selection: FACT -> SMART -> (LLM?) -> (NGRAM?) -> CLARIFY ---
        reply_text = _sanitize_reply(retrieve_fact_reply(user))

        if (not reply_text) and USE_SMART_RANKER and _SMART_IMPORTED:
            try:
                sr = smart_answer(user)
                if sr.get("ok") and sr.get("answer") and (sr.get("score",0.0) >= SMART_MIN_SCORE):
                    reply_text = _sanitize_reply(sr["answer"])
            except Exception:
                reply_text = ""

        # NOTE: LLM path intentionally disabled (HAVE_LLM=False)

        if (not reply_text) and HAVE_NGRAM and ngram_model:
            try:
                cand = (generate_reply(user, ngram_model, max_len=16, k=5) or "").strip()
                low = cand.lower().strip(" .!?,;:")
                reply_text = cand if (cand and len(low)>=4 and low not in {"ok","okay","hmm","k"}) else ""
            except Exception:
                reply_text = ""

        # Final: clarify (NEVER echo "ok.")
        if not reply_text:
            _append_pending(user)
            reply_text = build_clarify_prompt(user)

        # Persist reply tokens and print
        rw = tokenize_text(reply_text)
        r_tokens = words_to_tokens(rw, w2i, palette)
        manager.add_tokens("left", r_tokens)
        print(f"AI > {reply_text}")

        # remember last Q/A (for :teachlast)
        LAST_Q, LAST_A = user, reply_text

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
