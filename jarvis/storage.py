"""SQLite-backed local account, session and prompt history storage."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path

PASSWORD_ITERATIONS = 350_000
SESSION_TTL = 8 * 60 * 60
HISTORY_TTL = 7 * 24 * 60 * 60


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.path.parent.chmod(0o700)
        self._initialize()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("PRAGMA foreign_keys=ON")
            yield db
        finally:
            db.close()

    def _initialize(self) -> None:
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise RuntimeError("Database schema is newer than this Jarvis version")
            if version == 0:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        created_at INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS sessions (
                        token_hash TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        expires_at INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        prompt TEXT NOT NULL,
                        effort TEXT NOT NULL,
                        result TEXT,
                        state TEXT NOT NULL,
                        created_at INTEGER NOT NULL
                    );
                    PRAGMA user_version=1;
                """)
        if os.name != "nt":
            self.path.chmod(0o600)

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
        return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"

    @staticmethod
    def _check_password(password: str, encoded: str) -> bool:
        try:
            algorithm, rounds, salt, digest = encoded.split("$")
            if algorithm != "pbkdf2_sha256" or int(rounds) < 100_000:
                return False
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
            return hmac.compare_digest(actual, bytes.fromhex(digest))
        except (ValueError, TypeError):
            return False

    def has_admin(self) -> bool:
        with self.connect() as db:
            return db.execute("SELECT EXISTS(SELECT 1 FROM users)").fetchone()[0] == 1

    def enroll(self, username: str, password: str) -> bool:
        username = username.strip().lower()
        if not 3 <= len(username) <= 32 or not username.replace("_", "").isalnum():
            raise ValueError("Username must be 3–32 letters, numbers or underscores")
        if not 12 <= len(password) <= 256:
            raise ValueError("Password must be 12–256 characters")
        encoded = self._hash_password(password)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if db.execute("SELECT EXISTS(SELECT 1 FROM users)").fetchone()[0]:
                    db.rollback()
                    return False
                db.execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)", (username, encoded, int(time.time())))
                db.commit()
                return True
            except Exception:
                db.rollback()
                raise

    def authenticate(self, username: str, password: str) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT id,password_hash FROM users WHERE username=?", (username.strip().lower(),)).fetchone()
            # Same PBKDF2 work for unknown accounts; resist basic username enumeration.
            encoded = row["password_hash"] if row else self._hash_password("not-the-real-password", b"\x00" * 16)
            valid = self._check_password(password, encoded)
            if not row or not valid:
                return None
            token = secrets.token_urlsafe(32)
            db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (
                hashlib.sha256(token.encode()).hexdigest(), row["id"], int(time.time()) + SESSION_TTL))
            return token

    def current_user(self, token: str | None) -> dict | None:
        if not token or len(token) > 256:
            return None
        with self.connect() as db:
            row = db.execute("""SELECT u.id,u.username FROM sessions s JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires_at>?""", (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            return dict(row) if row else None

    def logout(self, token: str | None) -> None:
        if token:
            with self.connect() as db:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))

    def add_task(self, user_id: int, prompt: str, effort: str) -> int:
        with self.connect() as db:
            cursor = db.execute("INSERT INTO tasks(user_id,prompt,effort,state,created_at) VALUES(?,?,?,'running',?)", (
                user_id, prompt, effort, int(time.time())))
            return int(cursor.lastrowid)

    def finish_task(self, task_id: int, result: str | None, state: str) -> None:
        if state not in ("completed", "failed"):
            raise ValueError("Invalid task state")
        with self.connect() as db:
            db.execute("UPDATE tasks SET result=?,state=? WHERE id=? AND state='running'", (result, state, task_id))

    def history(self, user_id: int) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("""SELECT id,prompt,effort,result,state,created_at FROM tasks
                WHERE user_id=? ORDER BY id DESC LIMIT 20""", (user_id,))]

    def purge_expired(self) -> None:
        with self.connect() as db:
            now = int(time.time())
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            db.execute("DELETE FROM tasks WHERE created_at<?", (now - HISTORY_TTL,))
