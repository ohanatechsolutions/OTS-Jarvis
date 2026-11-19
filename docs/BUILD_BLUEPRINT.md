# OTS Jarvis — project-specific Build Blueprint

**Status:** Accepted concept; detailed behavior below is an implementation baseline, not proof of end-to-end product completion. **Updated:** 2026-11-18 HST. **Repository:** `ohanatechsolutions/OTS-Jarvis` (`main`). **Owner:** Ohana Tech Solutions. **Current deliverable:** local single-user pilot, not a deployable commercial appliance.

## A. Product definition and scope

Jarvis is a self-hosted, local-first AI business assistant that helps small business staff draft, research using approved local knowledge, and ultimately automate supervised workflows. Initial pilot: Island Craft Fairs (ICF). Users: business owner/admin and approximately three employees. Core job: ask a question or request work, understand what Jarvis plans to do, explicitly approve consequential actions, and audit outputs and time saved.

**Confirmed product direction from conversation (not yet verified in code):** Intel NUC 12 Enthusiast (i7-12700H/Arc A770M 16 GB/32 GB RAM/1 TB SSD); preferred Qwen3.5 9B local model, user-selectable Low/Medium/High plus AUTO default; browser/desktop client; secure admin-approved remote employee access; ICF central knowledge base; privacy-first automation; optional opt-in local work observer and value/savings measurement; no mandatory paid API, hosted AI, subscription or service. Commercial sale is future scope; internal name Jarvis may change.

**Provisional, reversible V1 pilot cutline:** One locally installed Windows 11 or Linux service, one administrator, localhost-only dashboard, authentication, manual text prompts to a separately installed OpenAI-compatible local model runner, deterministic output-depth selection, SQLite history, and explicit errors when offline. No business tools or unattended task execution are exposed in this pilot; this omission is a **scope boundary**, not a claim those previously requested features were canceled.

**Not in this pilot:** workforce accounts/MFA, remote/VPN access, live desktop control, browser action tools, editable knowledge base, voice, TanDM/Gmail/Sheets/Canva connectors, background activity monitoring, cloud inference, verified savings accounting, automatic updater, packaged appliance and general commercial licensing. Each remains in the backlog below.

**Success:** The first admin can enroll and sign in; authenticated prompt reaches a real local compatible runner and returns/stores its output; errors/denials are clear; no external cloud calls or unapproved actions occur; tests and an install/rollback procedure are documented. Hardware performance goal >=35 tokens/s (prefer >=40) is aspirational until measured on the NUC, not a product claim.

## B. User experience and acceptance journeys

**Screens:** local Jarvis web dashboard (`/`), one-time admin enrollment, sign-in, assistant form, local response, recent history, sign out. Responsive for desktop and mobile-sized local browsers, visible focus indicators, semantic labels, ARIA status. No decorative controls. UI is dark-mode only in pilot.

1. **New administrator:** Open localhost dashboard -> enrollment shown only if no accounts exist -> enter valid username and 12–256 character password -> account persisted with PBKDF2 hash -> login screen. Invalid fields show validation; second enrollment is rejected.
2. **Returning administrator:** Sign in -> authenticated cookie -> prompt entry, AUTO/Low/Medium/High response depth -> submit -> busy indicator -> local runner request -> display reply -> latest history. Invalid prompt/depth or concurrent model call is rejected; offline runner shows recoverable error and failed history item.
3. **Sign out:** Click sign out -> session revoked -> assistant and history are not accessible without login. Browser refresh returns to login.
4. **No network/runner:** Dashboard remains local; local runner failures do not initiate any external connection. Status shows failure. Retry requires a new explicit submission.
5. **Cancellation/undo:** This synchronous, non-action-taking pilot does not expose a fake cancel button. Closing the browser stops waiting but does not guarantee model inference cancellation. Agent cancellation and undo become mandatory with future automation tools.
6. **Permission-denied:** Unauthenticated history/task requests return HTTP 401; cross-origin writes and non-local host requests fail. Distinct roles and remote access are not enabled yet.

**State model:** no account -> enrolled/no session -> signed in/idle -> awaiting local model -> completed or failed -> idle; logout -> no session. Only local tasks and replies persist in SQLite for seven days; no background task execution exists.

## C. Functional requirements and test mapping

| ID | Priority | Trigger → validation → action/output | Acceptance / verification |
|---|---|---|---|
| REQ-001 | P0 | First run, valid admin credentials -> atomic enrollment/password hashing | One account only; second enrollment 409; invalid credentials rejected. `StoreTests`, `HTTPTests` |
| REQ-002 | P0 | Login/logout -> session issue/revoke; cookie HttpOnly/SameSite | Unauthenticated 401; successful login allows history; logout revokes token. `StoreTests`, `HTTPTests` |
| REQ-003 | P0 | Prompt and mode -> length/permission validation -> one local OpenAI-compatible inference request -> output/error | Valid prompt returns model reply; invalid blocked; offline 502; no cloud fallback. `ConfigTests`, `HTTPTests` |
| REQ-004 | P0 | Task processed -> SQLite result, depth, user and timestamp | Latest 20 sorted by ID, user ownership, local seven-day expiry; failed requests tracked. `StoreTests`, `HTTPTests` |
| REQ-005 | P0 | Configure runner URL -> validate hostname/scheme/path -> direct localhost HTTP | Reject remote IP/hostname, HTTPS, query and credentials. `ConfigTests` |
| REQ-006 | P0 | Browser state -> accessible form/status/history | Responsive app, text-only DOM insertion; manual browser UAT NOT RUN |
| REQ-007 | P1 | AUTO depth -> deterministic documented routing; explicit depth honored | Low/medium/high mapped to output token budgets, not asserted as internal model thinking mode. `EffortTests`, `HTTPTests` |
| REQ-008 | P1 | Employee enrollment/device approval/MFA -> role-scoped service access | NOT STARTED; requires architecture and security QA |
| REQ-009 | P1 | Supervised agent tool request -> preview -> admin approval -> bounded execution/audit/stop | NOT STARTED; no execution APIs enabled in pilot |
| REQ-010 | P1 | Secure remote access -> approved devices behind authenticated encrypted tunnel | NOT STARTED; no public listener or port forwarding |
| REQ-011 | P1 | ICF knowledge base and approved business adapters -> evidence-backed draft/actions | NOT STARTED; all vendor permissions and data flows need review |
| REQ-012 | P2 | Opt-in activity observer -> revocable consent -> local analysis/savings report | NOT STARTED; sensitive-data threat model required |
| REQ-013 | P1 | Windows packaging/update/install/uninstall and checksums | Windows build recipe prepared; Windows execution/install NOT RUN |
| REQ-014 | P1 | Model/NUC benchmarking -> measured t/s, RAM, GPU utilization, temperatures, stability | NOT RUN; no real model/NUC in this environment |

**Input/contract:** JSON `POST /api/setup {username,password}`, `POST /api/login {username,password}`, `POST /api/logout`, `POST /api/tasks {prompt,effort}`, `GET /api/me`, `GET /api/tasks`, `GET /api/health`. Responses use `{error}` on failure. No unrestricted tools, arbitrary URLs, file uploads or command endpoints. One request in flight to the model. HTTP header, origin and content type validation; maximum JSON body 32 KiB; prompt limit 8,000 characters; model response limit 2 MB; timeout 30 s; output caps low 256, medium 768, high 1,536 tokens. AUTO picks depth via deterministic, documented rules. This is **not** a true model-specific reasoning-effort switch.

## D. Nonfunctional requirements

- **Platforms:** Source pilot Python >=3.11; tested in Linux Python 3.13 only; intended Windows 11 x64 pending real install tests. Browser: current Chromium/Edge/Firefox pending manual UAT. Server interface always `127.0.0.1`.
- **Privacy/security:** Local model endpoint restricted to loopback HTTP; never accept arbitrary provider URLs; no telemetry, cloud API or third-party tokens. Admin passwords hashed with PBKDF2-HMAC-SHA256; sessions use random 256-bit token hashed at rest; sessions last up to eight hours; auth/login rate-limited in-process; basic origin/host checks, same-origin CSP. No SSL on loopback; MUST NOT internet-expose. Windows account/storage permissions and at-rest encryption NOT VERIFIED.
- **Retention:** Local prompt/response history expires after seven days at process startup. No export/delete UI yet; manual database reset documented. Backups/restore must be tested before any production use; this pilot is for synthetic or non-sensitive data only.
- **Reliability:** Fail closed for remote runner endpoints; bounded 30 s model calls; single concurrent model request with HTTP 429 busy feedback. No hidden unbounded retries. Error messages exclude prompt content. Graceful Ctrl+C. Actual model speed and recovery NOT VERIFIED.
- **Accessibility:** Native form controls, keyboard focus, ARIA live status, visible validation, responsive layout. Screen-reader and small-window testing remain open.
- **Cost:** Base software uses Python standard library with no runtime package dependency. Local runner/model require separate install and license review; no paid services authorized. Electricity/hardware and optional Windows CI minutes are not inherently free.

## E. Architecture and deployment

```text
Browser (localhost only)
    -> HTTP API + auth / origin checks (jarvis/server.py)
       -> local SQLite (jarvis/storage.py)
       -> deterministic depth router (jarvis/routing.py)
       -> direct loopback HTTP model adapter (jarvis/model.py)
           -> separately installed compatible local runner (Qwen3.5 9B target)
```

Repository source: `jarvis/` Python backend and `web/` assets, `tests/` stdlib automated tests, `docs/` product/evidence/release records, `scripts/` Windows build script, `.github/workflows/` manually triggered CI. No external execution surface.

Data model version 1: `users(id,username,password_hash,created_at)`, `sessions(token_hash,user_id,expires_at)`, `tasks(id,user_id,prompt,effort,result,state,created_at)`. No business data ingestion. SQLite WAL, foreign keys enabled, bounded connection timeout. Future migrations must be versioned/tested; refuses a newer database version.

Environment variables: `JARVIS_PORT` default 8745, `JARVIS_DATA_DIR` default per-user local app data, `JARVIS_MODEL` default `qwen3.5-9b` (runner model identifier may differ), `JARVIS_MODEL_ENDPOINT` default `http://127.0.0.1:1337/v1`. No API key required or accepted. A real compatible runner must be configured manually; no assumption all runners share naming or thinking controls.

**Installation:** Python >=3.11, `python -m jarvis`, or installed entrypoint `ots-jarvis`. The UI auto-opens locally. Windows `.exe` is intended as a console process in the pilot until verified desktop tray/background handling exists. A future installer must preserve user data, implement upgrade/rollback and pass Windows clean-machine smoke tests.

## F. Risks, mitigations and approvals

| ID | Risk | Control/gate |
|---|---|---|
| TH-001 | Compromised localhost service / DNS rebinding | Literal loopback bind, host/origin checks, authentication, CSP; negative tests |
| TH-002 | Prompt injection -> unauthorized tools | No agent tools in pilot; future explicit allowlist, approval, sandbox, cancel, red-team tests |
| TH-003 | Sensitive prompts stored plaintext in user profile | Synthetic/low-sensitivity test use only; encryption, deletion and protected backup before production |
| TH-004 | Local model endpoint silently routed to cloud | Strict loopback-only URL validation, direct `HTTPConnection`, no proxies, no cloud fallback |
| TH-005 | Unsigned Windows build / supply-chain compromise | SHA256 + real installer/Defender tests; signing/certificate decision before commercial release |
| TH-006 | Local NUC GPU/model or 64K context unsupported/slow | Hardware benchmark gate; no context/throughput guarantee until observed |
| TH-007 | Multiuser/remote access leaks customer data | Defer remote until MFA, device approval, VPN, tenant/role authorization and audit checks pass |
| TH-008 | External integration terms/fees differ | Verify APIs, licenses, quotas; no service activated without approval |

**Approval gates:** No spending, paid CI, cloud processing, outside email/posting, deletion of user data, elevated privileges, publicly exposed networking, publication or deployment without explicit authorization. Reversible source edits and synthetic local tests are authorized by BUILD mode.

## G. Delivery milestones and gates

1. **M0 repository truth/blueprint:** initialize source/README/test/docs on `main`, verify commit/readback and no overwrite. Gate: accessible source and traceability.
2. **M1 local assistant slice:** admin/auth, local prompt and reply, history, error states, negative tests. Gate: automated Linux API tests PASS and a *real* local runner smoke test (latter remains blocked), browser UAT.
3. **M2 safe agent control gateway:** scoped tool permissions, preview, durable approvals, audit, cancellation, recovery. Gate: prompt-injection and approval bypass tests, human supervised workflow.
4. **M3 employee/remote:** Google/MFA or equivalent login, role/device approval, authenticated VPN remote transport; no open port. Gate: adversarial auth and reconnect tests with ~3 concurrent users.
5. **M4 ICF knowledge/integrations:** approved knowledge ingestion and draft-only first Gmail/Sheets/website workflows. Gate: scope/license/API checks, synthetic + sandbox tests and reviewable actions.
6. **M5 Windows productization + real NUC:** per-user install, clean Win11 run/uninstall, Qwen 9B hardware benchmark, offline recovery, signed update/rollback. Gate: real `.exe`, SHA256, install logs, acceptance UAT, human security/release GO.
7. **M6 Impact/voice/commercial:** revocable opt-in observer, task savings proof, voice, commercial packaging only after data privacy and legal review.

**N/A now with reason:** store submission (not a mobile/browser extension product), subscriptions/payments (no checkout), multi-tenant cloud deployment (single localhost prototype). **Applicable specialized tracks:** Windows desktop 08.01, AI agent 08.05 (future tool controls), local-first 08.06 and NUC/edge 08.08.
