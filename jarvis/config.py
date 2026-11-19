"""Validated local-only runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ModelTarget:
    host: str
    port: int
    path: str


def parse_model_endpoint(endpoint: str) -> ModelTarget:
    """Allow only a direct loopback OpenAI-compatible model endpoint."""
    url = urlsplit(endpoint)
    if (
        url.scheme != "http"
        or url.hostname not in ("127.0.0.1", "localhost", "::1")
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
        or url.path not in ("", "/", "/v1", "/v1/")
    ):
        raise ValueError("JARVIS_MODEL_ENDPOINT must be a local http://loopback:port/v1 URL")
    try:
        port = url.port
    except ValueError as exc:
        raise ValueError("Invalid model endpoint port") from exc
    if not port:
        raise ValueError("Model endpoint port is required")
    return ModelTarget(url.hostname, port, "/v1/chat/completions")


def default_data_dir() -> Path:
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA")
        if not root:
            raise RuntimeError("LOCALAPPDATA is required on Windows")
        return Path(root) / "OhanaTechSolutions" / "Jarvis"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ots-jarvis"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    model: str
    target: ModelTarget
    port: int

    @classmethod
    def from_env(cls) -> "Settings":
        port = int(os.environ.get("JARVIS_PORT", "8745"))
        if not 0 <= port <= 65535:
            raise ValueError("JARVIS_PORT must be between 0 and 65535")
        model = os.environ.get("JARVIS_MODEL", "qwen3.5-9b").strip()
        if not 1 <= len(model) <= 120 or any(c in model for c in "\r\n\x00"):
            raise ValueError("JARVIS_MODEL must be a nonempty model identifier")
        return cls(
            data_dir=Path(os.environ.get("JARVIS_DATA_DIR") or default_data_dir()).expanduser(),
            model=model,
            target=parse_model_endpoint(os.environ.get("JARVIS_MODEL_ENDPOINT", "http://127.0.0.1:1337/v1")),
            port=port,
        )
