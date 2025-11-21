import sqlite3
import os
from datetime import datetime, timedelta
from config import DB_PATH


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users table
    cur.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            free_messages INTEGER DEFAULT 150,
            is_premium INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT,
            last_seen TEXT
        )"""
    )

    # --- Auto-migration: ensure is_admin column exists ---
    try:
        cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except:
        pass  # Ignore if already exists

    # Messages table
    cur.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )"""
    )

    # Documents table
    cur.execute(
        """CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            filename TEXT,
            pages INTEGER,
            uploaded_by_user_id INTEGER,
            approved_by_admin_id INTEGER,
            status TEXT,
            created_at TEXT,
            approved_at TEXT
        )"""
    )

    # Document chunks
    cur.execute(
        """CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            chunk_index INTEGER,
            content TEXT,
            token_count INTEGER,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        )"""
    )

    # Search table
    cur.execute(
        """CREATE VIRTUAL TABLE IF NOT EXISTS doc_search
            USING fts5(content)"""
    )

    # Regulatory alerts table
    cur.execute(
        """CREATE TABLE IF NOT EXISTS regulatory_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            body TEXT,
            created_at TEXT
        )"""
    )

    conn.commit()
    conn.close()


def _now():
    return datetime.utcnow().isoformat(timespec="seconds")


def get_or_create_user(chat_id: int, username: str = None, full_name: str = None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE users SET last_seen = ? WHERE chat_id = ?",
            (_now(), chat_id),
        )
        conn.commit()
        conn.close()
        return row

    cur.execute(
        """INSERT INTO users (chat_id, username, full_name, free_messages,
                              is_premium, is_admin, created_at, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (chat_id, username, full_name, 150, 0, 0, _now(), _now()),
    )
    conn.commit()
    cur.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_chat_id(chat_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_user_messages(user_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET free_messages = free_messages + ? WHERE id = ?",
        (delta, user_id),
    )
    conn.commit()
    conn.close()


def set_user_premium(chat_id: int, premium: bool = True):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET is_premium = ?, free_messages = ? WHERE chat_id = ?",
        (1 if premium else 0, 999999 if premium else 150, chat_id),
    )
    conn.commit()
    conn.close()


def save_message(user_id: int, role: str, content: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (user_id, role, content, _now()),
    )
    conn.commit()
    conn.close()


def insert_document(title, filename, pages, uploaded_by_user_id, status="pending"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO documents
            (title, filename, pages, uploaded_by_user_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
        (title, filename, pages, uploaded_by_user_id, status, _now()),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return doc_id


def update_document_status(doc_id: int, status: str, approved_by_admin_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if status == "approved":
        cur.execute(
            """UPDATE documents
                SET status = ?, approved_by_admin_id = ?, approved_at = ?
                WHERE id = ?""",
            (status, approved_by_admin_id, _now(), doc_id),
        )
    else:
        cur.execute(
            "UPDATE documents SET status = ? WHERE id = ?",
            (status, doc_id),
        )
    conn.commit()
    conn.close()


def add_document_chunk(document_id: int, chunk_index: int, content: str, token_count: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO document_chunks
            (document_id, chunk_index, content, token_count)
            VALUES (?, ?, ?, ?)""",
        (document_id, chunk_index, content, token_count),
    )
    chunk_id = cur.lastrowid
    cur.execute("INSERT INTO doc_search(rowid, content) VALUES (?, ?)", (chunk_id, content))
    conn.commit()
    conn.close()


def search_chunks(query: str, limit: int = 5):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT rowid, content FROM doc_search WHERE doc_search MATCH ? LIMIT ?",
        (query, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_chunk_by_id(chunk_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM document_chunks WHERE id = ?",
        (chunk_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def list_pending_documents():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE status = 'pending' ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_document(doc_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cur.fetchone()
    conn.close()
    return row


def insert_alert(title: str, body: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO regulatory_alerts (title, body, created_at) VALUES (?, ?, ?)",
        (title, body, _now()),
    )
    conn.commit()
    conn.close()


def list_alerts(limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM regulatory_alerts ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# --------------------------------------------------------------
#                   ADMIN HELPERS
# --------------------------------------------------------------

def set_user_admin(chat_id: int, is_admin: bool = True):
    """Mark a user as admin (or remove admin)."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()

    if row:
        cur.execute(
            "UPDATE users SET is_admin = ? WHERE chat_id = ?",
            (1 if is_admin else 0, chat_id),
        )
    else:
        cur.execute(
            """INSERT INTO users
               (chat_id, username, full_name, free_messages, is_premium,
                is_admin, created_at, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (chat_id, None, None, 150, 0, 1 if is_admin else 0, _now(), _now()),
        )

    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at ASC")
    rows = cur.fetchall()
    conn.close()
    return rows


def list_users_by_premium(is_premium: int):
    """Returns list of subscribed (1) or unsubscribed (0) users."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE is_premium = ? ORDER BY last_seen DESC",
        (is_premium,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_online_users(minutes: int = 15):
    """Users active in the last N minutes."""
    all_users = get_all_users()
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=minutes)

    result = []
    for u in all_users:
        last = u["last_seen"]
        if not last:
            continue

        try:
            dt = datetime.fromisoformat(last)
        except Exception:
            continue

        if dt >= cutoff:
            result.append(u)

    return result
