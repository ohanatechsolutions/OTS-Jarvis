# OTS Jarvis — Test Evidence

**Date:** 2026-11-18 HST (2026-11-19 UTC)  
**Environment:** Linux x86_64 / Python 3.13.5, local working-source tree.  
**Source version:** `0.1.0a1`. Remote commit SHA must be recorded after GitHub upload; local tests preceded commit.  
**Test fixtures:** temporary SQLite and synthetic OpenAI-compatible localhost test runner. Not a real Qwen model.

| Evidence | Check | Command | Observed result | Scope |
|---|---|---|---|---|
| E-001 | Unit + HTTP integration/negative tests | `PYTHONPATH=. python -W error::ResourceWarning -m unittest discover -s tests -v` | **PASS: 8 tests, 0 failures**, 2.6 seconds | Admin setup, auth, logout, model contract, unavailable model, URL/Host/Origin denial, schema guard, AUTO selection; fake local runner |
| E-009 | Installed-wheel smoke test | `python tests/smoke_installed.py` after `python -m pip wheel --no-deps --no-build-isolation . -w dist` | **PASS:** isolated venv offline wheel install, running server, health, HTML and JS assets | Real installed Python distribution; no model or Windows tests |
| E-002 | JavaScript syntax | `node --check jarvis/web/app.js` | **PASS** | Syntax only; not browser functional UAT |
| E-003 | Python compile | `python -m compileall -q jarvis` | **PASS** | Imports/syntax; not packaging/installer |
| E-004 | Actual local model inference | NOT RUN | **NOT RUN** — real Qwen3.5 9B and NUC unavailable | P0 runtime acceptance still open |
| E-005 | Windows PE/installer smoke/uninstall | NOT RUN | **NOT RUN** — no verified Windows build environment or authorized CI execution | Windows pre-release blocker |
| E-006 | Browser UX/accessibility | NOT RUN | **NOT RUN** — no interactive screen reader or Windows browser test | UI gate open |
| E-007 | Security/supply-chain independent review | NOT RUN | **NOT RUN** — source review and negative tests alone are insufficient | Before external/production use |
| E-008 | Model/GPU benchmark, power, context, concurrent staff | NOT RUN | **NOT RUN** — no NUC or real 9B runtime | NFR performance gate open |

**Interpretation:** The eight PASS tests include one end-to-end **API** request that traverses real HTTP, SQLite and a *fake* local model HTTP endpoint. It is *not* a full working Jarvis agent, actual model test, Windows installation test or approved release.
