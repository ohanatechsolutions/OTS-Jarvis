# OTS Jarvis

**Self-hosted AI assistance for business workflows — early local pilot.** By Ohana Tech Solutions.

> **Project status: IN DEVELOPMENT.** The repository currently implements a **single-user localhost assistant pilot**, not the full employee agent platform. The current release is not a validated Windows installer, and remote access/business automations are not enabled. See [Build Blueprint](docs/BUILD_BLUEPRINT.md), [Project Status](docs/PROJECT_STATUS.md) and [Test Evidence](docs/TEST_EVIDENCE.md).

## Why this exists

Small businesses waste time moving between inboxes, calendars, websites and repetitive admin tasks. Jarvis aims to consolidate knowledge and supervised automation into a private, local-first system that makes helpful work easier and high-impact actions accountable. The first milestone proves the smallest functional foundation: a secured local request to a local AI model, with task history and safe offline failure.

## Working pilot features

- One-time administrator enrollment and sign-in; local eight-hour sessions.
- Private localhost dashboard and authenticated prompts.
- OpenAI-compatible local model endpoint; no cloud fallback.
- **AUTO** (rule-based), Quick, Balanced and Detailed output depth. These modes currently change response token budget, **not guaranteed model internal thinking effort**.
- Local SQLite prompt/reply history for up to seven days.
- Explicit errors for invalid requests, busy or unavailable local models.

## Install and run from source

Requires Python **3.11+** and a *separately installed* local AI runner exposing an OpenAI-compatible chat-completions HTTP endpoint. The suggested model is Qwen3.5 9B; verify the model ID and endpoint in the runner. Jan, Ollama or another runner may require a different model ID/URL. **Never expose this service or runner to the internet.**

```powershell
# Windows PowerShell (from repository root)
$env:JARVIS_MODEL_ENDPOINT = "http://127.0.0.1:1337/v1"
$env:JARVIS_MODEL = "qwen3.5-9b"  # replace with the exact loaded runner model ID
python -m jarvis
```

```bash
# Linux (from repository root)
export JARVIS_MODEL_ENDPOINT=http://127.0.0.1:1337/v1
export JARVIS_MODEL=qwen3.5-9b   # actual model name may differ
python -m jarvis
```

Open `http://127.0.0.1:8745/`. On first launch, the **local console prints a one-time setup code**. Enter that code in the administrator enrollment form; do not share it. Once enrolled, later starts do not print a setup code. Model unavailable? The UI stays usable for enrollment/login/history and displays a clear offline error after a request. The pilot doesn't download a model or run without an installed runner.

Config: `JARVIS_PORT` (default 8745), `JARVIS_DATA_DIR` (per-user state), `JARVIS_MODEL`, `JARVIS_MODEL_ENDPOINT` (local URL `/v1`). Only `http://localhost`, `http://127.0.0.1` or IPv6 loopback are accepted for the model endpoint. Changing `JARVIS_PORT` requires choosing an available local port.

## Test

```bash
python -m unittest discover -s tests -v
python -m compileall -q jarvis
node --check jarvis/web/app.js  # if Node is installed
python -m pip wheel --no-deps --no-build-isolation . -w dist
python tests/smoke_installed.py  # isolated virtualenv smoke test
```

The HTTP integration tests use a **synthetic local model server**: they validate the API contract but **do not prove a real Qwen model, Windows installer or actual GPU performance**. Windows build instructions are in [Release Checklist](docs/RELEASE_CHECKLIST.md). No cloud API, paid service or telemetry is required by the application.

## Security and data handling

Jarvis binds **only to 127.0.0.1**, holds session tokens in HttpOnly SameSite cookies, hashes passwords with PBKDF2, and limits prompts, response sizes, concurrent calls and model request time. Prompt/response text is stored in a per-user SQLite file **without database encryption**; use only non-sensitive/synthetic test data until at-rest protections, access management and backup/deletion controls are vetted. No agent tools, shell access, remote employees or unapproved business messaging are available in this version.

## Roadmap

Next: production-grade task approvals and audit, trusted-device employee access, supervised browser/business connectors, ICF knowledge base, real NUC/Qwen benchmarking, Windows packaging/upgrade UAT, opt-in monitoring and measured savings. Each requires separate proof and security gates. Source-only collaboration is welcome; see project status for real blockers.
