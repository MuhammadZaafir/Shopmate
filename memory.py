"""
memory.py
---------
Lightweight persistent memory for ShopMate using SQLite.
Stores conversation turns per customer so the agent can:
  1. Recall earlier context in the same session
  2. Pick up a conversation days later without the customer repeating themselves
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "memory.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_message(customer_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (customer_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (customer_id, role, content, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_history(customer_id: str, limit: int = 20):
    """Return the last `limit` messages for a customer, oldest first."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM conversations WHERE customer_id = ? ORDER BY id DESC LIMIT ?",
        (customer_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]


def clear_history(customer_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM conversations WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()


# Ensure DB exists on import
init_db()
