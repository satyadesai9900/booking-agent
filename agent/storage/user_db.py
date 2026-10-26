"""
User & Session Store for MantaBooking.
Persists accounts and login sessions in the master SQLite database so they survive restarts
and are shared by every server process (e.g. multiple gunicorn workers).
- Passwords are stored as salted hashes (werkzeug scrypt/pbkdf2), never in plain text.
- Session tokens are random and only their SHA-256 digest is stored; sessions expire.
"""

import time
import uuid
import hashlib
import secrets
import datetime
import threading
import urllib.parse
from typing import Dict, Any, Optional

from werkzeug.security import generate_password_hash, check_password_hash

from agent.storage.booking_db import MASTER_DB_PATH, connect_sqlite

SESSION_TTL_SECONDS = 30 * 24 * 3600


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _avatar_for(name: str) -> str:
    encoded_name = urllib.parse.quote_plus(name)
    return f"https://api.dicebear.com/7.x/initials/svg?seed={encoded_name}&backgroundColor=4f46e5"


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """User fields that are safe to return to the client."""
    return {key: user[key] for key in ("id", "email", "name", "role", "avatar")}


class UserStore:
    def __init__(self, db_path: str = MASTER_DB_PATH):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            conn = connect_sqlite(self.db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'traveler',
                        avatar TEXT,
                        created_at TEXT NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        token_hash TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        expires_at REAL NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
                conn.commit()
            finally:
                conn.close()

    def create_user(self, email: str, name: str, password: str, role: str = "traveler") -> Optional[Dict[str, Any]]:
        """Creates a user. Returns None if the email is already registered."""
        user = {
            "id": f"usr_{uuid.uuid4().hex[:12]}",
            "email": email.strip().lower(),
            "name": name.strip(),
            "role": role,
            "avatar": _avatar_for(name.strip()),
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self.lock:
            conn = connect_sqlite(self.db_path)
            try:
                conn.execute(
                    "INSERT INTO users (id, email, name, password_hash, role, avatar, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
                    (user["id"], user["email"], user["name"], generate_password_hash(password),
                     user["role"], user["avatar"], user["created_at"]),
                )
                conn.commit()
            except Exception as e:
                if "UNIQUE" in str(e):
                    return None
                raise
            finally:
                conn.close()
        return user

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = connect_sqlite(self.db_path)
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        conn = connect_sqlite(self.db_path)
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?;", (email.strip().lower(),)).fetchone()
        finally:
            conn.close()
        if row and check_password_hash(row["password_hash"], password):
            return dict(row)
        return None

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.lock:
            conn = connect_sqlite(self.db_path)
            try:
                conn.execute("DELETE FROM sessions WHERE expires_at < ?;", (time.time(),))
                conn.execute(
                    "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?);",
                    (_token_digest(token), user_id, time.time() + SESSION_TTL_SECONDS),
                )
                conn.commit()
            finally:
                conn.close()
        return token

    def get_user_for_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        conn = connect_sqlite(self.db_path)
        try:
            row = conn.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?;",
                (_token_digest(token), time.time()),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_session(self, token: str):
        with self.lock:
            conn = connect_sqlite(self.db_path)
            try:
                conn.execute("DELETE FROM sessions WHERE token_hash = ?;", (_token_digest(token),))
                conn.commit()
            finally:
                conn.close()


user_store = UserStore()
