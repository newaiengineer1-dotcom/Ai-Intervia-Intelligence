import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("intervia.db")


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, role TEXT, industry TEXT, turns_json TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    con.commit()
    con.close()


def save_session(session_id: str, role: str, industry: str, turns: list[dict]):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO sessions(session_id, role, industry, turns_json) VALUES(?,?,?,?) "
        "ON CONFLICT(session_id) DO UPDATE SET role=excluded.role, industry=excluded.industry, turns_json=excluded.turns_json, updated_at=CURRENT_TIMESTAMP",
        (session_id, role, industry, json.dumps(turns, ensure_ascii=False)),
    )
    con.commit()
    con.close()
