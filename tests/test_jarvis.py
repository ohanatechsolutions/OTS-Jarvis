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


class HTTPTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
