# OTS Jarvis — Test Evidence

**Date:** 2026-11-18 HST (2026-11-19 UTC)  
**Environment:** Linux x86_64 / Python 3.13.5, local working-source tree.  
**Source version:** `0.1.0a2` under development. Parent verified remote baseline `c846439860c43399d85e23182a9e46fd184e94f9`; new Git commit must be recorded after GitHub push.  
**Test fixtures:** temporary SQLite and synthetic OpenAI-compatible localhost test runner. Not a real Qwen model.

| Evidence | Check | Command | Observed result | Scope |
|---|---|---|---|---|
| E-001 | Unit + HTTP integration/negative tests | `PYTHONPATH=. python -W error::ResourceWarning -m unittest discover -s tests -v` | **PASS: 16 tests, 0 failures**, 4.8 seconds | Admin setup, auth, logout, model contract, unavailable model, URL/Host/Origin denial, schema guard, AUTO selection; supervised local notes with explicit approval/cancel/undo, pause/reject, expired proposal, migration, restart recovery, concurrency and redacted audit; fake local model runner for model-contract check |
| E-009 | Installed-wheel smoke test | `python tests/smoke_installed.py` after `python -m pip wheel --no-deps --no-build-isolation . -w dist` | **PASS:** isolated venv offline wheel install, running server, health, HTML and JS assets | Real installed Python distribution; no model or Windows tests |
| E-002 | JavaScript syntax | `node --check jarvis/web/app.js` | **PASS** | Syntax only; not browser functional UAT |
| E-003 | Python compile | `python -m compileall -q jarvis` | **PASS** | Imports/syntax; not packaging/installer |
| E-012 | v0.1.0a2 local distributable | `python -m pip wheel --no-deps --no-build-isolation . -w dist` then `python tests/smoke_installed.py` | **PASS**, built `ots_jarvis-0.1.0a2-py3-none-any.whl` (19,140 bytes); isolated environment installed wheel without index; served health, HTML and JS | Linux Python 3.13.5 only; NOT a Windows `.exe` |
| E-010 | REQ-009-A approval & database tests | `python -W error::ResourceWarning -m unittest discover -s tests -v` | **PASS**, including local SQLite approvals, duplicate execution conflict, concurrent race, v1→v2 migration, wrong-owner/unauthenticated/cross-origin denial, cancellation, expiry, undo and pause | All tool behavior is genuinely local SQLite note persistence, no external actions |
| E-011 | Real Chromium browser automation | `PYTHONPATH=. python tests/browser_smoke.py` | **BLOCKED**: `net::ERR_BLOCKED_BY_ADMINISTRATOR` navigating to local `127.0.0.1`; browser policy was not bypassed | UI behavior needs real human/UAT check on an ordinary machine |
| E-004 | Actual local model inference | NOT RUN | **NOT RUN** — real Qwen3.5 9B and NUC unavailable | P0 runtime acceptance still open |
| E-005 | Windows PE/installer smoke/uninstall | NOT RUN | **NOT RUN** — no verified Windows build environment or authorized CI execution | Windows pre-release blocker |
| E-006 | Browser UX/accessibility | NOT RUN | **NOT RUN** — no interactive screen reader or Windows browser test | UI gate open |
| E-007 | Security/supply-chain independent review | NOT RUN | **NOT RUN** — source review and negative tests alone are insufficient | Before external/production use |
| E-008 | Model/GPU benchmark, power, context, concurrent staff | NOT RUN | **NOT RUN** — no NUC or real 9B runtime | NFR performance gate open |

**Interpretation:** The passing tests include an end-to-end **API** request that traverses real HTTP, SQLite and a *fake* local model HTTP endpoint. It is *not* a full working Jarvis agent, actual model test, Windows installation test or approved release.
