"""Smoke-test a wheel in an isolated Python environment; no real AI required."""

import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
import venv
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    import tomllib
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    wheels = list((root / "dist").glob(f"ots_jarvis-{version}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Exactly one Jarvis {version} wheel required")
    with tempfile.TemporaryDirectory(prefix="jarvis-wheel-smoke-") as tmp:
        t = Path(tmp)
        venv.EnvBuilder(with_pip=True).create(t / "venv")
        python = t / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheels[0])], check=True, stdout=subprocess.DEVNULL)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "JARVIS_PORT": str(port), "JARVIS_DATA_DIR": str(t / "user-data")}
        env.pop("PYTHONPATH", None)
        proc = subprocess.Popen([str(python), "-m", "jarvis", "--no-browser"], cwd=t, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for _ in range(40):
                if proc.poll() is not None:
                    raise RuntimeError("Installed Jarvis exited prematurely")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as response:
                        health = json.load(response)
                    break
                except Exception:
                    time.sleep(0.15)
            else:
                raise TimeoutError("Installed Jarvis health endpoint not responding")
            assert health["status"] == "ok" and health["version"] == version
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                assert b"OTS Jarvis" in response.read()
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/app.js", timeout=2) as response:
                assert b"refresh();" in response.read()
            print("PASS: isolated wheel install, server startup, HTTP health, HTML and JS assets")
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()


if __name__ == "__main__":
    main()
