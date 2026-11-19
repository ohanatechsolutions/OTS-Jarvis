"""Limited OpenAI-compatible local model request adapter; no cloud fallback."""

from __future__ import annotations

import http.client
import json
from .config import ModelTarget

MAX_RESPONSE_BYTES = 2_000_000
OUTPUT_TOKENS = {"low": 256, "medium": 768, "high": 1536}


class ModelError(Exception):
    """Sanitized, user-actionable model transport error."""


def ask_local_model(target: ModelTarget, model: str, prompt: str, effort: str) -> str:
    if effort not in OUTPUT_TOKENS:
        raise ValueError("Invalid effort")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": OUTPUT_TOKENS[effort],
    }).encode("utf-8")
    connection = http.client.HTTPConnection(target.host, target.port, timeout=30)
    try:
        connection.request("POST", target.path, body=body, headers={
            "Content-Type": "application/json", "Accept": "application/json"})
        response = connection.getresponse()
        length = response.getheader("Content-Length")
        if length and int(length) > MAX_RESPONSE_BYTES:
            raise ModelError("Local model response exceeded size limit")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ModelError("Local model response exceeded size limit")
        if response.status != 200:
            raise ModelError(f"Local model returned HTTP {response.status}; check runner and model name")
        data = json.loads(raw)
        reply = data["choices"][0]["message"]["content"]
        if not isinstance(reply, str) or not reply.strip():
            raise ModelError("Local model returned an empty response")
        return reply[:100_000]
    except (OSError, TimeoutError) as exc:
        raise ModelError("Local model unavailable or timed out; start your local runner") from exc
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelError("Local model returned an invalid response") from exc
    finally:
        connection.close()
