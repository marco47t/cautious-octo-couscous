import sqlite3
import uuid
from datetime import datetime, timezone
from utils.logger import logger

DB_PATH = "facts.db"

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                category    TEXT DEFAULT 'general',
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                full_fact   TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON facts(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_key  ON facts(user_id, key)")
        conn.commit()

def upsert_fact(user_id: str, key: str, value: str, full_fact: str, category: str = "general"):
    """Insert new fact or update if same key already exists for this user."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM facts WHERE user_id=? AND key=?", (user_id, key)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE facts SET value=?, full_fact=?, updated_at=? WHERE id=?",
                (value, full_fact, now, existing["id"])
            )
            logger.debug(f"[facts] Updated: {key}={value} for user {user_id}")
        else:
            conn.execute(
                "INSERT INTO facts VALUES (?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), user_id, category, key, value, full_fact, now, now)
            )
            logger.debug(f"[facts] Stored: {key}={value} for user {user_id}")
        conn.commit()

def search_facts(user_id: str, query: str) -> list[dict]:
    """Keyword search across key, value, and full_fact fields."""
    words = [w for w in query.lower().split() if len(w) > 2]
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM facts WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,)
        ).fetchall()

    results = []
    for row in rows:
        searchable = f"{row['key']} {row['value']} {row['full_fact']}".lower()
        score = sum(1 for w in words if w in searchable)
        if score > 0:
            results.append({
                "fact": row["full_fact"],
                "key": row["key"],
                "value": row["value"],
                "category": row["category"],
                "score": score,
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:5]

def get_all_facts(user_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM facts WHERE user_id=? ORDER BY category, key",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def delete_fact(user_id: str, key: str) -> bool:
    with _conn() as conn:
        cursor = conn.execute(
            "DELETE FROM facts WHERE user_id=? AND key=?", (user_id, key)
        )
        conn.commit()
        return cursor.rowcount > 0
