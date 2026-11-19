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

from .actions import (
    ACTION_TTL_SECONDS, MAX_PENDING_ACTIONS, MAX_SAVED_NOTES,
    ActionConflict, note_digest, now_seconds, validate_note,
)

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
            if version > 2:
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
            if version <= 1:
                # A transaction prevents a partially initialized action gateway.
                db.execute("BEGIN IMMEDIATE")
                try:
                    db.execute("""CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        text TEXT NOT NULL,
                        created_at INTEGER NOT NULL
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS action_requests (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        kind TEXT NOT NULL CHECK(kind='save_note'),
                        state TEXT NOT NULL CHECK(state IN
                            ('pending','completed','cancelled','expired','undone')),
                        payload TEXT,
                        payload_sha256 TEXT NOT NULL,
                        note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS action_events (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        action_id INTEGER REFERENCES action_requests(id) ON DELETE CASCADE,
                        event TEXT NOT NULL,
                        created_at INTEGER NOT NULL
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS action_controls (
                        id INTEGER PRIMARY KEY CHECK(id=1),
                        paused INTEGER NOT NULL CHECK(paused IN (0,1)) DEFAULT 0
                    )""")
                    db.execute("INSERT OR IGNORE INTO action_controls(id,paused) VALUES(1,0)")
                    db.execute("CREATE INDEX IF NOT EXISTS idx_actions_user ON action_requests(user_id,id DESC)")
                    db.execute("CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id,id DESC)")
                    db.execute("PRAGMA user_version=2")
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
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
            # Redacted audit records are retained for 90 days. Delete only
            # terminal actions; permanent notes remain until explicitly undone.
            # Keep approved actions while their notes exist so the UI can always
            # expose the exact undo operation even after ninety days.
            db.execute("""DELETE FROM action_requests WHERE
                (state IN ('cancelled','expired','undone') OR
                 (state='completed' AND note_id IS NULL))
                AND updated_at<?""", (now - 90 * 24 * 3600,))
            db.execute("""UPDATE tasks SET state='failed',
                result='Interrupted by local server restart; retry manually'
                WHERE state='running'""")
            db.execute("DELETE FROM action_events WHERE action_id IS NULL AND created_at<?",
                       (now - 90 * 24 * 3600,))

    def action_snapshot(self, user_id: int) -> dict:
        """Return the owner's pending previews, saved notes and redacted log."""
        with self.connect() as db:
            now = now_seconds()
            db.execute("BEGIN IMMEDIATE")
            self._expire_actions(db, user_id, now)
            db.commit()
            actions = [dict(row) for row in db.execute("""
                SELECT id,kind,state,payload AS preview,payload_sha256,created_at,
                       expires_at,updated_at,note_id FROM action_requests
                WHERE user_id=? ORDER BY id DESC LIMIT 20""", (user_id,))]
            notes = [dict(row) for row in db.execute("""
                SELECT n.id,n.text,n.created_at,a.id AS action_id
                FROM notes n LEFT JOIN action_requests a ON a.note_id=n.id
                WHERE n.user_id=? ORDER BY n.id DESC LIMIT 100""", (user_id,))]
            events = [dict(row) for row in db.execute("""
                SELECT id,action_id,event,created_at FROM action_events
                WHERE user_id=? ORDER BY id DESC LIMIT 40""", (user_id,))]
            paused = bool(db.execute("SELECT paused FROM action_controls WHERE id=1").fetchone()[0])
            return {"paused": paused, "actions": actions, "notes": notes, "events": events}

    @staticmethod
    def _event(db, user_id: int, action_id: int, event: str, now: int) -> None:
        db.execute("INSERT INTO action_events(user_id,action_id,event,created_at) VALUES(?,?,?,?)",
                   (user_id, action_id, event, now))

    def _expire_actions(self, db, user_id: int, now: int) -> None:
        expired = db.execute("""SELECT id FROM action_requests
            WHERE user_id=? AND state='pending' AND expires_at<=?""", (user_id, now)).fetchall()
        for item in expired:
            changed = db.execute("""UPDATE action_requests SET state='expired',payload=NULL,updated_at=?
                WHERE id=? AND user_id=? AND state='pending'""", (now, item["id"], user_id))
            if changed.rowcount:
                self._event(db, user_id, item["id"], "expired", now)

    def propose_note(self, user_id: int, text: object) -> dict:
        """Never perform the operation here. Persist the exact preview for review."""
        validated = validate_note(text)
        now = now_seconds()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._expire_actions(db, user_id, now)
                if db.execute("SELECT paused FROM action_controls WHERE id=1").fetchone()[0]:
                    raise ActionConflict("Actions are paused")
                total = db.execute("""SELECT COUNT(*) FROM action_requests
                    WHERE user_id=? AND state='pending'""", (user_id,)).fetchone()[0]
                if total >= MAX_PENDING_ACTIONS:
                    raise ActionConflict("Too many pending actions; cancel one first")
                cursor = db.execute("""INSERT INTO action_requests
                    (user_id,kind,state,payload,payload_sha256,created_at,expires_at,updated_at)
                    VALUES(?,'save_note','pending',?,?,?,?,?)""",
                    (user_id, validated, note_digest(validated), now, now+ACTION_TTL_SECONDS, now))
                action_id = cursor.lastrowid
                self._event(db, user_id, action_id, "proposed", now)
                db.commit()
                return {"id": action_id, "kind": "save_note", "state": "pending",
                        "preview": validated, "expires_at": now+ACTION_TTL_SECONDS}
            except Exception:
                db.rollback()
                raise

    def transition_action(self, user_id: int, action_id: int, decision: str) -> dict:
        """State transition, side effect and audit record commit atomically."""
        if decision not in ("approve", "cancel", "undo"):
            raise ValueError("Unsupported action decision")
        now = now_seconds()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._expire_actions(db, user_id, now)
                row = db.execute("""SELECT * FROM action_requests WHERE id=? AND user_id=?""",
                                 (action_id, user_id)).fetchone()
                if not row:
                    raise LookupError("Action not found")
                if decision == "approve" and row["state"] == "pending":
                    if db.execute("SELECT paused FROM action_controls WHERE id=1").fetchone()[0]:
                        raise ActionConflict("Actions are paused")
                    if row["kind"] != "save_note" or row["payload"] is None:
                        raise ActionConflict("Action has no executable payload")
                    existing = db.execute("SELECT COUNT(*) FROM notes WHERE user_id=?", (user_id,)).fetchone()[0]
                    if existing >= MAX_SAVED_NOTES:
                        raise ActionConflict("Note limit reached; undo a saved note first")
                    # Reconfirm exact approved bytes before performing the effect.
                    if note_digest(row["payload"]) != row["payload_sha256"]:
                        raise ActionConflict("Action preview integrity check failed")
                    cur = db.execute("INSERT INTO notes(user_id,text,created_at) VALUES(?,?,?)",
                                     (user_id, row["payload"], now))
                    state, event, note_id = "completed", "approved_and_executed", cur.lastrowid
                    db.execute("""UPDATE action_requests
                        SET state=?,payload=NULL,note_id=?,updated_at=? WHERE id=?""",
                        (state, note_id, now, action_id))
                elif decision == "cancel" and row["state"] == "pending":
                    state, event, note_id = "cancelled", "cancelled", None
                    db.execute("""UPDATE action_requests SET state=?,payload=NULL,updated_at=?
                        WHERE id=?""", (state, now, action_id))
                elif decision == "undo" and row["state"] == "completed":
                    state, event, note_id = "undone", "undone", None
                    db.execute("UPDATE action_requests SET state=?,updated_at=? WHERE id=?",
                               (state, now, action_id))
                    db.execute("DELETE FROM notes WHERE id=? AND user_id=?", (row["note_id"], user_id))
                else:
                    raise ActionConflict("Action cannot transition from its current state")
                self._event(db, user_id, action_id, event, now)
                db.commit()
                return {"id": action_id, "state": state, "note_id": note_id}
            except Exception:
                db.rollback()
                raise

    def set_actions_paused(self, user_id: int, paused: bool) -> bool:
        """Global local emergency stop; only the enrolled admin can reach it."""
        if type(paused) is not bool:
            raise ValueError("paused must be true or false")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                # Check that the authenticated owner actually exists.
                if not db.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
                    raise LookupError("User not found")
                db.execute("UPDATE action_controls SET paused=? WHERE id=1", (int(paused),))
                db.execute("""INSERT INTO action_events(user_id,action_id,event,created_at)
                    VALUES(?,NULL,?,?)""", (user_id, "paused" if paused else "resumed", now_seconds()))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return paused
