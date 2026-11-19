"""Local-only functional, negative and HTTP integration checks."""

import http.client
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jarvis.config import ModelTarget, Settings, parse_model_endpoint
from jarvis.model import ModelError, ask_local_model
from jarvis.server import JarvisServer
from jarvis.routing import resolve_depth
from jarvis.storage import Store


class FakeLocalRunner(BaseHTTPRequestHandler):
    calls = []
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        self.calls.append(payload)
        body = json.dumps({"choices": [{"message": {"content": "Local test response"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class ConfigTests(unittest.TestCase):
    def test_local_target_only(self):
        target = parse_model_endpoint("http://localhost:1337/v1")
        self.assertEqual((target.host, target.port, target.path), ("localhost", 1337, "/v1/chat/completions"))
        for bad in ["https://127.0.0.1:1337/v1", "http://0.0.0.0:1337/v1", "http://192.168.1.2:1337/v1", "http://evil.test:1337/v1", "http://127.0.0.1:1337/v1?x=1", "http://user:pass@127.0.0.1:1337/v1", "http://127.0.0.1:1337/v1/../../admin", "http://127.0.0.1/v1"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_model_endpoint(bad)


class EffortTests(unittest.TestCase):
    def test_auto_routing_and_explicit_depth(self):
        self.assertEqual(resolve_depth("auto", "Hello"), "low")
        self.assertEqual(resolve_depth("auto", "Please draft an invitation"), "medium")
        self.assertEqual(resolve_depth("auto", "Analyze this security review"), "high")
        self.assertEqual(resolve_depth("medium", "Analyze this security review"), "medium")
        with self.assertRaises(ValueError):
            resolve_depth("invalid", "hello")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "private" / "jarvis.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_enrollment_login_logout_and_history(self):
        self.assertFalse(self.store.has_admin())
        self.assertTrue(self.store.enroll("Admin", "Passphrase-long-123"))
        self.assertFalse(self.store.enroll("Another", "Another-long-password"))
        with self.store.connect() as db:
            row = db.execute("SELECT username,password_hash FROM users").fetchone()
            self.assertEqual(row["username"], "admin")
            self.assertNotIn("Passphrase-long-123", row["password_hash"])
        self.assertIsNone(self.store.authenticate("admin", "wrong"))
        token = self.store.authenticate("admin", "Passphrase-long-123")
        self.assertIsNotNone(token)
        user = self.store.current_user(token)
        task = self.store.add_task(user["id"], "Example question", "low")
        self.store.finish_task(task, "Example answer", "completed")
        self.assertEqual(self.store.history(user["id"])[0]["result"], "Example answer")
        self.store.logout(token)
        self.assertIsNone(self.store.current_user(token))

    def test_enroll_rejects_invalid_input(self):
        for username, password in [("a", "123456789012"), ("admin", "weak"), ("name!", "strong-123456")]:
            with self.subTest(username=username), self.assertRaises(ValueError):
                self.store.enroll(username, password)

    def test_database_schema_future_guard(self):
        with self.store.connect() as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaises(RuntimeError):
            Store(self.store.path)


class HTTPHarness:
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeLocalRunner)
        cls.fake_thread = threading.Thread(target=cls.fake.serve_forever, daemon=True)
        cls.fake_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.fake.shutdown()
        cls.fake.server_close()
        cls.fake_thread.join(timeout=3)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.temp.name), "local-test-model", ModelTarget("127.0.0.1", self.fake.server_port, "/v1/chat/completions"), 0)
        self.app = JarvisServer(("127.0.0.1", 0), self.settings)
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = None

    def tearDown(self):
        self.app.shutdown()
        self.app.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def request(self, method, path, data=None, headers=None):
        con = http.client.HTTPConnection("127.0.0.1", self.app.server_port, timeout=5)
        props = dict(headers or {})
        if self.cookie: props["Cookie"] = self.cookie
        body = None
        if data is not None:
            body = json.dumps(data)
            props.setdefault("Content-Type", "application/json")
        con.request(method, path, body=body, headers=props)
        res = con.getresponse()
        raw = res.read()
        result = json.loads(raw) if path.startswith("/api/") else raw
        if res.getheader("Set-Cookie") and "jarvis_session=" in res.getheader("Set-Cookie") and "Max-Age=0" not in res.getheader("Set-Cookie"):
            self.cookie = res.getheader("Set-Cookie").split(";",1)[0]
        result_tuple = (res.status, result, dict(res.getheaders()))
        con.close()
        return result_tuple

    def login(self):
        self.assertEqual(self.request("POST", "/api/setup", {"username":"admin", "password":"correct-long-password", "setup_code":self.app.setup_token})[0], 201)
        self.assertEqual(self.request("POST", "/api/login", {"username":"admin", "password":"correct-long-password"})[0], 200)

class HTTPTests(HTTPHarness, unittest.TestCase):
    def test_browser_workflow_real_http_and_mock_model(self):
        self.assertEqual(self.request("GET", "/api/me")[1]["enrollment_required"], True)
        self.assertEqual(self.request("GET", "/")[0], 200)
        self.assertEqual(self.request("GET", "/app.js")[0], 200)
        self.assertEqual(self.request("GET", "/style.css")[0], 200)
        self.assertEqual(self.request("GET", "/api/tasks")[0], 401)
        self.login()
        status, result, headers = self.request("POST", "/api/tasks", {"prompt":"Write a short draft", "effort":"medium"})
        self.assertEqual(status, 200)
        self.assertEqual(result["reply"], "Local test response")
        self.assertEqual(self.request("GET", "/api/tasks")[1]["tasks"][0]["state"], "completed")
        self.assertEqual(self.request("POST", "/api/tasks", {"prompt":"Analyze this business process", "effort":"auto"})[1]["resolved_effort"], "high")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("POST", "/api/logout")[0], 200)
        self.cookie = None
        self.assertEqual(self.request("GET", "/api/tasks")[0], 401)

    def test_auth_csrf_enrollment_and_input_denials(self):
        self.assertEqual(self.request("POST", "/api/tasks", {"prompt":"hi", "effort":"low"})[0], 401)
        self.assertEqual(self.request("POST", "/api/setup", {"username":"admin", "password":"correct-long-password", "setup_code":"wrong"})[0], 403)
        self.login()
        self.assertEqual(self.request("POST", "/api/setup", {"username":"other", "password":"other-long-password", "setup_code":"guess"})[0], 409)
        self.assertEqual(self.request("POST", "/api/tasks", {"prompt":"", "effort":"low"})[0], 400)
        self.assertEqual(self.request("POST", "/api/tasks", {"prompt":"x"*8001, "effort":"low"})[0], 400)
        self.assertEqual(self.request("POST", "/api/tasks", {"prompt":"hello", "effort":"super"})[0], 400)
        self.assertEqual(self.request("POST", "/api/tasks", {"prompt":"hello", "effort":"low"}, {"Origin":"http://evil.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/tasks", {"prompt":"hello", "effort":"low"}, {"Host":"evil.example"})[0], 403)
        self.assertEqual(self.request("GET", "/api/nope")[0], 404)

    def test_local_model_unavailable_has_persisted_failure(self):
        self.login()
        self.app.settings = Settings(Path(self.temp.name), "local-test-model", ModelTarget("127.0.0.1", 1, "/v1/chat/completions"), 0)
        status, response, _ = self.request("POST", "/api/tasks", {"prompt":"hello", "effort":"low"})
        self.assertEqual(status, 502)
        self.assertEqual(response["state"], "failed")
        self.assertEqual(self.request("GET", "/api/tasks")[1]["tasks"][0]["state"], "failed")




class ActionStoreTests(unittest.TestCase):
    """Exercise genuine SQLite transactions and migration without model stubs."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "jarvis.sqlite3"
        self.store = Store(self.path)
        self.assertTrue(self.store.enroll("admin", "correct-long-password"))
        self.user_id = self.store.current_user(self.store.authenticate("admin", "correct-long-password"))["id"]

    def tearDown(self):
        self.temp.cleanup()

    def test_pending_is_no_side_effect_until_explicit_approval_and_undo(self):
        plan = self.store.propose_note(self.user_id, "Private research note")
        snapshot = self.store.action_snapshot(self.user_id)
        self.assertEqual(snapshot["notes"], [])
        self.assertEqual(snapshot["actions"][0]["preview"], "Private research note")
        self.assertEqual(snapshot["events"][0]["event"], "proposed")
        result = self.store.transition_action(self.user_id, plan["id"], "approve")
        self.assertEqual(result["state"], "completed")
        snapshot = self.store.action_snapshot(self.user_id)
        self.assertEqual(snapshot["notes"][0]["text"], "Private research note")
        self.assertIsNone(snapshot["actions"][0]["preview"])
        with self.assertRaises(Exception) as ctx:
            self.store.transition_action(self.user_id, plan["id"], "approve")
        self.assertEqual(type(ctx.exception).__name__, "ActionConflict")
        self.assertEqual(len(self.store.action_snapshot(self.user_id)["notes"]), 1)
        self.assertEqual(self.store.transition_action(self.user_id, plan["id"], "undo")["state"], "undone")
        self.assertEqual(self.store.action_snapshot(self.user_id)["notes"], [])
        with self.assertRaises(Exception) as ctx:
            self.store.transition_action(self.user_id, plan["id"], "undo")
        self.assertEqual(type(ctx.exception).__name__, "ActionConflict")
        actions = self.store.action_snapshot(self.user_id)
        self.assertEqual([a["event"] for a in actions["events"][:3]],
                         ["undone", "approved_and_executed", "proposed"])
        self.assertNotIn("Private research note", str(actions["events"]))

    def test_cancel_expiry_pause_and_wrong_owner_fail_closed(self):
        first = self.store.propose_note(self.user_id, "cancel me")["id"]
        self.assertEqual(self.store.transition_action(self.user_id, first, "cancel")["state"], "cancelled")
        with self.assertRaises(Exception):
            self.store.transition_action(self.user_id, first, "approve")
        second = self.store.propose_note(self.user_id, "expire me")["id"]
        with self.store.connect() as db:
            db.execute("UPDATE action_requests SET expires_at=0 WHERE id=?", (second,))
        with self.assertRaises(Exception):
            self.store.transition_action(self.user_id, second, "approve")
        self.assertEqual(self.store.action_snapshot(self.user_id)["actions"][0]["state"], "expired")
        third = self.store.propose_note(self.user_id, "pause me")["id"]
        self.assertTrue(self.store.set_actions_paused(self.user_id, True))
        with self.assertRaises(Exception):
            self.store.propose_note(self.user_id, "blocked")
        with self.assertRaises(Exception):
            self.store.transition_action(self.user_id, third, "approve")
        self.assertEqual(self.store.transition_action(self.user_id, third, "cancel")["state"], "cancelled")
        self.assertFalse(self.store.set_actions_paused(self.user_id, False))
        with self.assertRaises(LookupError):
            self.store.transition_action(999, first, "undo")
        self.assertEqual(self.store.action_snapshot(self.user_id)["notes"], [])

    def test_reopen_v2_database_and_reject_future_schema(self):
        action = self.store.propose_note(self.user_id, "persistent")
        reopened = Store(self.path)
        self.assertEqual(reopened.transition_action(self.user_id, action["id"], "approve")["state"], "completed")
        self.assertEqual(Store(self.path).action_snapshot(self.user_id)["notes"][0]["text"], "persistent")
        with reopened.connect() as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaises(RuntimeError):
            Store(self.path)


class ActionHTTPTests(HTTPHarness, unittest.TestCase):
    """Real HTTP+SQLite routes; fake model never participates in approvals."""

    def test_actions_require_admin_and_reject_invalid_or_cross_origin(self):
        payload = {"kind": "save_note", "text": "Private local note"}
        self.assertEqual(self.request("GET", "/api/actions")[0], 401)
        self.assertEqual(self.request("POST", "/api/actions/propose", payload)[0], 401)
        self.login()
        self.assertEqual(self.request("POST", "/api/actions/propose", payload, {"Origin":"http://malicious.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/actions/propose", {"kind":"shell", "text":"whoami"})[0], 400)
        self.assertEqual(self.request("POST", "/api/actions/propose", {"kind":"save_note", "text":""})[0], 400)
        self.assertEqual(self.request("POST", "/api/actions/decision", {"id":True,"decision":"approve"})[0], 400)
        self.assertEqual(self.request("POST", "/api/actions/decision", {"id":999,"decision":"approve"})[0], 404)
        self.assertEqual(self.request("POST", "/api/actions/pause", {"paused":"true"})[0], 400)
        self.assertEqual(self.request("POST", "/api/actions/propose", {"kind":"save_note", "text":"X" * 4001})[0], 400)

    def test_approval_cancel_undo_pause_and_logout_real_http(self):
        self.login()
        code, proposal, _ = self.request("POST", "/api/actions/propose", {"kind":"save_note", "text":"Meeting checklist"})
        self.assertEqual(code, 201)
        self.assertEqual(self.request("GET", "/api/actions")[1]["notes"], [])
        self.assertEqual(self.request("POST", "/api/actions/pause", {"paused":True})[0], 200)
        self.assertEqual(self.request("POST", "/api/actions/decision", {"id":proposal["id"], "decision":"approve"})[0], 409)
        self.assertEqual(self.request("POST", "/api/actions/pause", {"paused":False})[0], 200)
        self.assertEqual(self.request("POST", "/api/actions/decision", {"id":proposal["id"], "decision":"approve"})[1]["state"], "completed")
        self.assertEqual(self.request("POST", "/api/actions/decision", {"id":proposal["id"], "decision":"approve"})[0], 409)
        snap = self.request("GET", "/api/actions")[1]
        self.assertEqual(snap["notes"][0]["text"], "Meeting checklist")
        self.assertEqual(snap["notes"][0]["action_id"], proposal["id"])
        self.assertEqual(self.request("POST", "/api/actions/decision", {"id":proposal["id"], "decision":"undo"})[1]["state"], "undone")
        self.assertEqual(self.request("GET", "/api/actions")[1]["notes"], [])
        second = self.request("POST", "/api/actions/propose", {"kind":"save_note", "text":"cancel"})[1]["id"]
        self.assertEqual(self.request("POST", "/api/actions/decision", {"id":second, "decision":"cancel"})[1]["state"], "cancelled")
        self.assertEqual(self.request("POST", "/api/logout")[0], 200)
        self.cookie = None
        self.assertEqual(self.request("GET", "/api/actions")[0], 401)


class ActionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "jarvis.sqlite3"
        self.store = Store(self.path)
        self.store.enroll("admin", "long-private-test-password")
        self.uid = self.store.current_user(self.store.authenticate("admin", "long-private-test-password"))["id"]

    def tearDown(self):
        self.temp.cleanup()

    def test_double_approval_race_creates_exactly_one_note(self):
        from concurrent.futures import ThreadPoolExecutor
        from jarvis.actions import ActionConflict
        id_ = self.store.propose_note(self.uid, "must be created once")["id"]
        def approve(_):
            try:
                self.store.transition_action(self.uid, id_, "approve")
                return "completed"
            except ActionConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(pool.map(approve, [1, 2]))
        self.assertEqual(outcomes, ["completed", "conflict"])
        self.assertEqual(len(self.store.action_snapshot(self.uid)["notes"]), 1)

    def test_migration_from_real_previous_v1_and_restart_recovery(self):
        action = self.store.propose_note(self.uid, "existing note")
        with self.store.connect() as db:
            db.execute("DROP TABLE action_events")
            db.execute("DROP TABLE action_requests")
            db.execute("DROP TABLE action_controls")
            db.execute("DROP TABLE notes")
            db.execute("PRAGMA user_version=1")
        migration = Store(self.path)
        self.assertEqual(migration.action_snapshot(self.uid)["actions"], [])
        self.assertEqual(migration.propose_note(self.uid, "new note")["state"], "pending")
        with migration.connect() as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)
        id_ = migration.add_task(self.uid, "Unfinished request", "low")
        migration.purge_expired()
        self.assertEqual(migration.history(self.uid)[0]["state"], "failed")
        self.assertIn("Interrupted", migration.history(self.uid)[0]["result"])

    def test_duplicate_server_port_does_not_recover_active_task(self):
        settings = Settings(Path(self.temp.name), "unused", ModelTarget("127.0.0.1", 1, "/v1/chat/completions"), 0)
        with JarvisServer(("127.0.0.1", 0), settings) as active:
            task = active.store.add_task(self.uid, "in flight", "low")
            with self.assertRaises(OSError):
                JarvisServer(("127.0.0.1", active.server_port), settings)
            self.assertEqual(active.store.history(self.uid)[0]["id"], task)
            self.assertEqual(active.store.history(self.uid)[0]["state"], "running")

    def test_undo_preserved_after_old_action_audit_purge(self):
        id_ = self.store.propose_note(self.uid, "saved for months")["id"]
        self.store.transition_action(self.uid, id_, "approve")
        with self.store.connect() as db:
            db.execute("UPDATE action_requests SET updated_at=1 WHERE id=?", (id_,))
        self.store.purge_expired()
        self.assertEqual(self.store.transition_action(self.uid, id_, "undo")["state"], "undone")
        self.assertEqual(self.store.action_snapshot(self.uid)["notes"], [])


if __name__ == "__main__":
    unittest.main()
