"""Loopback-only HTTP frontend and authenticated assistant API."""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import socket
import hmac
import threading
from email.message import Message
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__
from .actions import ActionConflict
from .config import Settings
from .model import ModelError, ask_local_model
from .storage import Store
from .routing import resolve_depth

LOG = logging.getLogger("jarvis")
MAX_BODY = 32768


class JarvisServer(ThreadingHTTPServer):
    daemon_threads = True
    # Prevent a second process from binding this local service port.
    allow_reuse_address = False
    allow_reuse_port = False

    def server_bind(self) -> None:
        # On Windows SO_REUSEADDR may permit a second bind; exclusive mode
        # protects the active local service from port takeover.
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        super().server_bind()

    def __init__(self, address: tuple[str, int], settings: Settings):
        # Always bind to loopback, even when called by an embedder.
        if address[0] != "127.0.0.1":
            raise ValueError("Jarvis only supports the 127.0.0.1 interface")
        # Reserve the listening socket before touching persistent data. A
        # duplicate launch on the same port must never alter the active app's
        # task state or run startup recovery unexpectedly.
        super().__init__(address, JarvisHandler)
        try:
            self.settings = settings
            self.store = Store(settings.data_dir / "jarvis.sqlite3")
            self.store.purge_expired()
            self.setup_token = secrets.token_urlsafe(24) if not self.store.has_admin() else None
            self.model_semaphore = threading.BoundedSemaphore(1)
            self.login_lock = threading.Lock()
            self.login_attempts: list[float] = []
        except Exception:
            self.server_close()
            raise


class JarvisHandler(BaseHTTPRequestHandler):
    server: JarvisServer
    server_version = "JarvisLocal/0.1"
    sys_version = ""

    def log_message(self, fmt: str, *args: object) -> None:
        # Avoid URLs, bodies, tokens or user-supplied values in logs.
        LOG.info("http_request method=%s status=%s", self.command, args[1] if len(args) > 1 else "unknown")

    def _headers(self, status: int, mime: str = "application/json; charset=utf-8", cookie: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _json(self, status: int, obj: dict | list, cookie: str | None = None) -> None:
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._headers(status, cookie=cookie)
        self.wfile.write(raw)

    def _cookie(self) -> str | None:
        try:
            parsed = SimpleCookie()
            parsed.load(self.headers.get("Cookie", "")[:512])
            return parsed["jarvis_session"].value if "jarvis_session" in parsed else None
        except Exception:
            return None

    def _user(self) -> dict | None:
        return self.server.store.current_user(self._cookie())

    def _host_is_local(self) -> bool:
        host = self.headers.get("Host", "")
        return host in (
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        )

    def _origin_is_local(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin in (
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        )

    def _read_json(self) -> dict:
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if not 2 <= length <= MAX_BODY:
            raise ValueError("Request exceeds size limit or has no JSON body")
        raw = self.rfile.read(length)
        try:
            decoded = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Malformed JSON") from exc
        if not isinstance(decoded, dict):
            raise ValueError("JSON object expected")
        return decoded

    def do_GET(self) -> None:
        if not self._host_is_local():
            self._json(HTTPStatus.FORBIDDEN, {"error": "Host not allowed"})
            return
        path = urlsplit(self.path).path
        if path in ("/", "/app.js", "/style.css"):
            name = "index.html" if path == "/" else path[1:]
            mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}[name]
            contents = (files("jarvis") / "web" / name).read_bytes()
            self._headers(HTTPStatus.OK, mime)
            self.wfile.write(contents)
            return
        if path == "/api/health":
            self._json(HTTPStatus.OK, {"status": "ok", "version": __version__})
            return
        if path == "/api/me":
            user = self._user()
            self._json(HTTPStatus.OK, {"enrollment_required": not self.server.store.has_admin(), "user": user})
            return
        if path in ("/api/tasks", "/api/actions"):
            user = self._user()
            if not user:
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "Sign in required"})
                return
            if path == "/api/tasks":
                self._json(HTTPStatus.OK, {"tasks": self.server.store.history(user["id"])})
            else:
                self._json(HTTPStatus.OK, self.server.store.action_snapshot(user["id"]))
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:
        if not self._host_is_local() or not self._origin_is_local():
            self._json(HTTPStatus.FORBIDDEN, {"error": "Cross-origin request denied"})
            return
        path = urlsplit(self.path).path
        if path not in ("/api/setup", "/api/login", "/api/logout", "/api/tasks",
                        "/api/actions/propose", "/api/actions/decision", "/api/actions/pause"):
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        user = self._user()
        if path == "/api/logout":
            if not user:
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "Sign in required"})
                return
            self.server.store.logout(self._cookie())
            self._json(HTTPStatus.OK, {"ok": True}, "jarvis_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict")
            return
        try:
            data = self._read_json()
            if path == "/api/setup":
                self._setup(data)
            elif path == "/api/login":
                self._login(data)
            elif path == "/api/tasks":
                self._task(data, user)
            else:
                self._action(path, data, user)
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except LookupError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Action not found"})
        except ActionConflict as exc:
            self._json(HTTPStatus.CONFLICT, {"error": str(exc)})

    def _setup(self, data: dict) -> None:
        if set(data) != {"username", "password", "setup_code"} or not all(isinstance(x, str) for x in data.values()):
            raise ValueError("Username, password and setup code are required")
        expected = self.server.setup_token
        if expected is None:
            self._json(HTTPStatus.CONFLICT, {"error": "Administrator already enrolled"})
            return
        if not hmac.compare_digest(data["setup_code"], expected):
            self._json(HTTPStatus.FORBIDDEN, {"error": "Invalid local setup code"})
            return
        if self.server.store.enroll(data["username"], data["password"]):
            self.server.setup_token = None
            self._json(HTTPStatus.CREATED, {"ok": True, "next": "login"})
        else:
            self._json(HTTPStatus.CONFLICT, {"error": "Administrator already enrolled"})

    def _login(self, data: dict) -> None:
        if set(data) != {"username", "password"} or not all(isinstance(x, str) for x in data.values()):
            raise ValueError("Username and password are required")
        import time
        with self.server.login_lock:
            now = time.monotonic()
            self.server.login_attempts = [t for t in self.server.login_attempts if now - t < 60]
            if len(self.server.login_attempts) >= 5:
                self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "Too many attempts; retry in one minute"})
                return
            self.server.login_attempts.append(now)
        token = self.server.store.authenticate(data["username"], data["password"])
        if not token:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "Invalid credentials"})
            return
        self._json(HTTPStatus.OK, {"ok": True}, f"jarvis_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800")


    def _action(self, path: str, data: dict, user: dict | None) -> None:
        # No model output, web page or external client can directly approve an
        # action. Only the authenticated local admin's separate HTTP request can.
        if not user:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "Sign in required"})
            return
        if path == "/api/actions/propose":
            if set(data) != {"kind", "text"} or data["kind"] != "save_note":
                raise ValueError("Only the save_note local action is supported")
            self._json(HTTPStatus.CREATED, self.server.store.propose_note(user["id"], data["text"]))
        elif path == "/api/actions/decision":
            if set(data) != {"id", "decision"} or type(data["id"]) is not int or data["id"] <= 0:
                raise ValueError("Valid integer action ID and decision required")
            if type(data["decision"]) is not str:
                raise ValueError("Invalid decision")
            self._json(HTTPStatus.OK, self.server.store.transition_action(user["id"], data["id"], data["decision"]))
        elif path == "/api/actions/pause":
            if set(data) != {"paused"} or type(data["paused"]) is not bool:
                raise ValueError("paused must be true or false")
            paused = self.server.store.set_actions_paused(user["id"], data["paused"])
            self._json(HTTPStatus.OK, {"paused": paused})

    def _task(self, data: dict, user: dict | None) -> None:
        if not user:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "Sign in required"})
            return
        if set(data) != {"prompt", "effort"}:
            raise ValueError("Prompt and effort are required")
        prompt, effort = data["prompt"], data["effort"]
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 8000:
            raise ValueError("Prompt must contain 1–8000 characters")
        if effort not in ("auto", "low", "medium", "high"):
            raise ValueError("Effort must be auto, low, medium or high")
        resolved = resolve_depth(effort, prompt.strip())
        if not self.server.model_semaphore.acquire(blocking=False):
            self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "Local model busy; retry shortly"})
            return
        try:
            task_id = self.server.store.add_task(user["id"], prompt.strip(), resolved)
            try:
                reply = ask_local_model(self.server.settings.target, self.server.settings.model, prompt.strip(), resolved)
                self.server.store.finish_task(task_id, reply, "completed")
                self._json(HTTPStatus.OK, {"id": task_id, "reply": reply, "state": "completed", "resolved_effort": resolved})
            except ModelError as exc:
                self.server.store.finish_task(task_id, str(exc), "failed")
                self._json(HTTPStatus.BAD_GATEWAY, {"id": task_id, "error": str(exc), "state": "failed"})
        finally:
            self.server.model_semaphore.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OTS Jarvis local pilot (never internet-exposed)")
    parser.add_argument("--no-browser", action="store_true", help="Do not launch a browser")
    args = parser.parse_args()
    settings = Settings.from_env()
    logging.basicConfig(level=logging.WARNING)
    with JarvisServer(("127.0.0.1", settings.port), settings) as app:
        url = f"http://127.0.0.1:{app.server_port}/"
        print(f"Jarvis listening locally at {url}", flush=True)
        if app.setup_token:
            print(f"One-time local administrator setup code: {app.setup_token}", flush=True)
            print("Keep this code private; enter it in the first-run dashboard.", flush=True)
        if not args.no_browser:
            import webbrowser
            webbrowser.open(url)
        try:
            app.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
