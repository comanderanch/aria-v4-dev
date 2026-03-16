#!/usr/bin/env python3
import json, math, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FACTS = BASE / "memory" / "facts_index.json"

def _norm(s:str)->str: return re.sub(r"[^a-z0-9\s]+"," ", s.lower()).strip()
def _tok(s:str): return [t for t in _norm(s).split() if t]

def _load_facts():
    if not FACTS.exists(): return []
    try: return json.loads(FACTS.read_text(encoding="utf-8")).get("facts",[])
    except Exception: return []

def _idf(all_q_tokens):
    N = len(all_q_tokens); df={}
    for toks in all_q_tokens:
        for t in set(toks): df[t]=df.get(t,0)+1
    return {t:(math.log((N+1)/(df[t]+1))+1.0) for t in df}

def _vec(tokens, idf):
    tf={}; 
    for t in tokens: tf[t]=tf.get(t,0)+1
    L=len(tokens) or 1
    return {t:(tf[t]/L)*idf.get(t,0.0) for t in tf}

def _cos(a,b):
    dot=sum(a.get(t,0)*b.get(t,0) for t in set(a)|set(b))
    na=math.sqrt(sum(v*v for v in a.values())) or 1e-9
    nb=math.sqrt(sum(v*v for v in b.values())) or 1e-9
    return dot/(na*nb)

def smart_answer(question:str):
    facts=_load_facts()
    if not facts: return {"ok":False,"error":"no anchors; run :ingestfacts","answer":""}
    q_tokens=[_tok(f.get("q_norm") or f.get("q","")) for f in facts]
    idf=_idf(q_tokens)
    qv=_vec(_tok(question), idf)
    best=(-1.0, None)
    for f,toks in zip(facts,q_tokens):
        sv=_vec(toks, idf); score=_cos(qv, sv)
        if score>best[0]: best=(score,f)
    f=best[1]; 
    return {"ok":True,"score":round(best[0],4),"question":f.get("q",""),"answer":f.get("a","")}

if __name__=="__main__":
    q=" ".join(sys.argv[1:]).strip()
    print(json.dumps(smart_answer(q), ensure_ascii=False))
