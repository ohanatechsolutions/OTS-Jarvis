# OTS Jarvis — Test Evidence

**Date:** 2026-11-18 HST (2026-11-19 UTC)  
**Environment:** Linux x86_64 / Python 3.13.5, local working-source tree.  
**Source version:** `0.1.0a2` under development. Parent verified remote baseline `c846439860c43399d85e23182a9e46fd184e94f9`; new Git commit must be recorded after GitHub push.  
**Test fixtures:** temporary SQLite and synthetic OpenAI-compatible localhost test runner. Not a real Qwen model.

| Evidence | Check | Command | Observed result | Scope |
|---|---|---|---|---|
| E-001 | Unit + HTTP integration/negative tests | `PYTHONPATH=. python -W error::ResourceWarning -m unittest discover -s tests -v` | **PASS: 17 tests, 0 failures**, 4.5 seconds | Admin setup, auth, logout, model contract, unavailable model, URL/Host/Origin denial, schema guard, AUTO selection; supervised local notes with explicit approval/cancel/undo, pause/reject, expired proposal, migration, restart recovery, concurrency and redacted audit; fake local model runner for model-contract check |
| E-009 | Installed-wheel smoke test | `python tests/smoke_installed.py` after `python -m pip wheel --no-deps --no-build-isolation . -w dist` | **PASS:** isolated venv offline wheel install, running server, health, HTML and JS assets | Real installed Python distribution; no model or Windows tests |
| E-002 | JavaScript syntax | `node --check jarvis/web/app.js` | **PASS** | Syntax only; not browser functional UAT |
| E-003 | Python compile | `python -m compileall -q jarvis` | **PASS** | Imports/syntax; not packaging/installer |
| E-013 | Duplicate-port startup safety | `python -W error::ResourceWarning -m unittest discover -s tests -v` | **PASS:** duplicate listener fails before startup recovery touches active user's task rows | Same-port duplicate process; alternate-port same-profile concurrency remains unverified |
| E-012 | v0.1.0a2 local distributable | `python -m pip wheel --no-deps --no-build-isolation . -w dist` then `python tests/smoke_installed.py` | **PASS**, built `ots_jarvis-0.1.0a2-py3-none-any.whl` (19,140 bytes); isolated environment installed wheel without index; served health, HTML and JS | Linux Python 3.13.5 only; NOT a Windows `.exe` |
| E-010 | REQ-009-A approval & database tests | `python -W error::ResourceWarning -m unittest discover -s tests -v` | **PASS**, including local SQLite approvals, duplicate execution conflict, concurrent race, v1→v2 migration, wrong-owner/unauthenticated/cross-origin denial, cancellation, expiry, undo and pause | All tool behavior is genuinely local SQLite note persistence, no external actions |
| E-011 | Real Chromium browser automation | `PYTHONPATH=. python tests/browser_smoke.py` | **BLOCKED**: `net::ERR_BLOCKED_BY_ADMINISTRATOR` navigating to local `127.0.0.1`; browser policy was not bypassed | UI behavior needs real human/UAT check on an ordinary machine |
| E-004 | Actual local model inference | NOT RUN | **NOT RUN** — real Qwen3.5 9B and NUC unavailable | P0 runtime acceptance still open |
| E-005 | Windows PE/installer smoke/uninstall | NOT RUN | **NOT RUN** — no verified Windows build environment or authorized CI execution | Windows pre-release blocker |
| E-006 | Browser UX/accessibility | NOT RUN | **NOT RUN** — no interactive screen reader or Windows browser test | UI gate open |
| E-007 | Security/supply-chain independent review | NOT RUN | **NOT RUN** — source review and negative tests alone are insufficient | Before external/production use |
| E-008 | Model/GPU benchmark, power, context, concurrent staff | NOT RUN | **NOT RUN** — no NUC or real 9B runtime | NFR performance gate open |

**Interpretation:** The passing tests include an end-to-end **API** request that traverses real HTTP, SQLite and a *fake* local model HTTP endpoint. It is *not* a full working Jarvis agent, actual model test, Windows installation test or approved release.

## E-018 — Actual Windows x64 executable CI build (2026-11-19 UTC)

- Public-repository standard `windows-latest` hosted runner, Python 3.13, PyInstaller 6.15.0. GitHub Actions run: https://github.com/ohanatechsolutions/OTS-Jarvis/actions/runs/44469707466 — **SUCCESS** on build branch `exe-pilot-build-20261118`, commit `f09d43bebbae1eb455da989a51c038813ec32ff3`.
- Windows unit/HTTP integration suite, PyInstaller one-file executable packaging, executable startup and localhost `/api/health` smoke check, and SHA-256 generation: workflow completed successfully.
- Artifact `OTS-Jarvis-Windows-pilot-unsigned`, ID `14503159770`; ZIP artifact expires 2026-12-03 UTC.
- Downloaded executable `OTS-Jarvis.exe` independently inspected: 10,371,842 bytes; `MZ` and `PE\\0\\0` headers, AMD64 machine `0x8664`, PE32+ `0x20b`. SHA-256 `2bc33db96ce172b4900f7ad57b3f876922468e08ec00e88b9007ae6facb30216` matches the workflow-generated checksum. Download ZIP SHA-256 was independently recorded by GitHub: `5457657bfaa116d8c7085a3d34a175908f41e5451f3a83ae9ae6808b90faa393`.
- **Not run:** clean Windows user-device double-click/login UAT, SmartScreen/Defender reputation, real Jan/Qwen runner, NUC performance, Windows install/uninstall (portable executable, not an installer), multiuser/remote/security production gates. Unsigned. **NO-GO for general release; suitable as a limited pilot for owner-supervised testing**.
- Prior first Windows build run `44469467231` failed a real duplicate-port security test because Windows allows socket reuse differently. Remediated by `SO_EXCLUSIVEADDRUSE` and disabling address reuse; passing subsequent run `44469707466`. Test was not skipped.
