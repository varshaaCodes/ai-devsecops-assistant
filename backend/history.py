# backend/history.py
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.getenv("HISTORY_DB", "/app/reports/analysis_history.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    c = _conn()
    cur = c.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT,
        repo_or_project TEXT,
        number INTEGER,
        ai_review TEXT,
        pdf_path TEXT,
        severity_json TEXT,
        diff_snippet TEXT,
        posted_comment INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)
    c.commit()
    c.close()

def save_analysis(platform, repo_or_project, number, ai_review, pdf_path, severity_counts, diff_snippet, posted):
    c = _conn()
    cur = c.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO analyses (platform, repo_or_project, number, ai_review, pdf_path, severity_json, diff_snippet, posted_comment, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (platform, repo_or_project, number, ai_review, pdf_path, json.dumps(severity_counts), diff_snippet, int(posted), now))
    c.commit()
    rid = cur.lastrowid
    c.close()
    return rid

def list_analyses(limit=100):
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT id, platform, repo_or_project, number, pdf_path, severity_json, posted_comment, created_at FROM analyses ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    c.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "platform": r[1],
            "repo_or_project": r[2],
            "number": r[3],
            "pdf_path": r[4],
            "severity": json.loads(r[5]) if r[5] else {},
            "posted_comment": bool(r[6]),
            "created_at": r[7],
        })
    return out

def get_analysis(aid):
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT id, platform, repo_or_project, number, ai_review, pdf_path, severity_json, diff_snippet, posted_comment, created_at FROM analyses WHERE id = ?", (aid,))
    r = cur.fetchone()
    c.close()
    if not r:
        return {}
    return {
        "id": r[0], "platform": r[1], "repo_or_project": r[2], "number": r[3],
        "ai_review": r[4], "pdf_path": r[5], "severity": json.loads(r[6]) if r[6] else {},
        "diff_snippet": r[7], "posted_comment": bool(r[8]), "created_at": r[9]
    }

# initialize
init_db()
