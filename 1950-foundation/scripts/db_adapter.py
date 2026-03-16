#!/usr/bin/env python3
import sqlite3, json, hashlib
from pathlib import Path
from datetime import datetime

_DB_PATH = None

def _now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def init_db(path: str) -> None:
    """Initialize SQLite DB at path (creates tables if missing)."""
    global _DB_PATH
    _DB_PATH = Path(path)
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_DB_PATH))
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS profiles(
      id TEXT PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      created_ts TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS qa_pairs(
      id TEXT PRIMARY KEY,
      profile_id TEXT,
      q TEXT NOT NULL,
      a TEXT NOT NULL,
      q_norm TEXT NOT NULL,
      a_norm TEXT NOT NULL,
      created_ts TEXT NOT NULL,
      FOREIGN KEY(profile_id) REFERENCES profiles(id)
    );
    CREATE TABLE IF NOT EXISTS anchors(
      id TEXT PRIMARY KEY,
      qa_id TEXT NOT NULL,
      q_tokens TEXT NOT NULL,
      a_tokens TEXT NOT NULL,
      hemisphere_q TEXT NOT NULL,
      hemisphere_a TEXT NOT NULL,
      created_ts TEXT NOT NULL,
      FOREIGN KEY(qa_id) REFERENCES qa_pairs(id)
    );
    CREATE TABLE IF NOT EXISTS pending(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      text TEXT NOT NULL,
      created_ts TEXT NOT NULL
    );
    """)
    con.commit()
    con.close()

def _profile_id(name: str) -> str:
    nm = (name or "base").strip().lower()
    return hashlib.sha256(("profile:"+nm).encode("utf-8")).hexdigest()[:16]

def upsert_profile(name: str) -> str:
    """Return stable profile id; create row if missing."""
    pid = _profile_id(name)
    con = sqlite3.connect(str(_DB_PATH))
    con.execute("INSERT OR IGNORE INTO profiles(id, name, created_ts) VALUES(?,?,?)",
                (pid, (name or "base").strip().lower(), _now()))
    con.commit()
    con.close()
    return pid

def _qa_id(qn: str, an: str) -> str:
    return hashlib.sha256(("qa||"+qn+"||"+an).encode("utf-8")).hexdigest()[:16]

def write_qa_pair(profile_name: str, q: str, a: str, q_norm: str, a_norm: str,
                  anchor_id: str, q_tokens, a_tokens,
                  hemisphere_q: str = "RIGHT", hemisphere_a: str = "LEFT") -> None:
    """Dual-write a QA pair and its anchor/tokens."""
    pid = upsert_profile(profile_name or "base")
    qaid = _qa_id(q_norm, a_norm)
    con = sqlite3.connect(str(_DB_PATH))
    con.execute(
        "INSERT OR IGNORE INTO qa_pairs(id, profile_id, q, a, q_norm, a_norm, created_ts) "
        "VALUES(?,?,?,?,?,?,?)",
        (qaid, pid, q, a, q_norm, a_norm, _now())
    )
    con.execute(
        "INSERT OR IGNORE INTO anchors(id, qa_id, q_tokens, a_tokens, hemisphere_q, hemisphere_a, created_ts) "
        "VALUES(?,?,?,?,?,?,?)",
        (anchor_id, qaid, json.dumps(q_tokens, ensure_ascii=False),
         json.dumps(a_tokens, ensure_ascii=False), hemisphere_q, hemisphere_a, _now())
    )
    con.commit()
    con.close()

def add_pending(text: str) -> None:
    con = sqlite3.connect(str(_DB_PATH))
    con.execute("INSERT INTO pending(text, created_ts) VALUES(?,?)", (text, _now()))
    con.commit()
    con.close()

def list_qa_pairs(profile_name: str | None = None, limit: int = 1000):
    con = sqlite3.connect(str(_DB_PATH))
    cur = con.cursor()
    if profile_name:
        pid = _profile_id(profile_name)
        cur.execute("SELECT q,a FROM qa_pairs WHERE profile_id=? ORDER BY rowid LIMIT ?", (pid, limit))
    else:
        cur.execute("SELECT q,a FROM qa_pairs ORDER BY rowid LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()
    return rows
