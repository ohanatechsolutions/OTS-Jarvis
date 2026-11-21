# OTS Jarvis — Project Status

**Updated:** 2026-11-18 HST, slice `REQ-009-A`. **Owner:** Ohana Tech Solutions. **Baseline:** Newly established source pilot; earlier v0.2.0 installer ZIP and Git bundle exist in Library but raw bytes were unavailable to the active workspace. This code is a distinct reconstructed pilot baseline, not an asserted import of that historical code.

**GitHub:** `ohanatechsolutions/OTS-Jarvis`; default branch `main`. **Source test environment:** Linux, Python 3.13.5. **Source version:** `0.1.0a2`; currently published baseline remains 0.1.0a1 until verified remote commit. **Windows pre-release:** NO-GO. **Python wheel:** clean isolated venv install/HTTP asset smoke PASS for v0.1.0a2 (E-012); not an `.exe`.

| Requirement | Status | Evidence/limitation | Next |
|---|---|---|---|
| REQ-001 local admin enrollment | IN PROGRESS | Automated store+HTTP tests PASS incl. first-run setup code; manual browser UAT not run | Test on clean Windows profile |
| REQ-002 login/session/logout | IN PROGRESS | Automated HTTP tests PASS; Windows browser UAT pending | Manual auth/expiry tests |
| REQ-003 local AI inference adapter | IN PROGRESS | Contract tests PASS against fake localhost runner; **real Qwen NOT RUN** | Configure local runner and benchmark |
| REQ-004 local task history | IN PROGRESS | HTTP/store tests PASS; restart now marks interrupted model tasks failed, after binding socket to avoid corrupting an active same-port instance | Verify seven-day retention and recovery on Windows |
| REQ-005 local URL security | IN PROGRESS | Negative URL/Origin/Host checks PASS | Independent security review |
| REQ-006 UI/accessibility | IN PROGRESS | HTML/CSS/JS implemented; JS syntax checked | Manual keyboard/mobile/screen-reader UAT |
| REQ-007 deterministic AUTO routing | IN PROGRESS | Unit/integration PASS | Confirm UX with owner on real model |
| REQ-008 multiuser/MFA | NOT STARTED | Beyond single-admin pilot | Design authentication and device enrollment |
| REQ-009 agent tool approval | IN PROGRESS | Sub-slice `REQ-009-A`: authenticated local note planning, immutable preview, atomic approval/execute, cancel/undo, pause/resume, 10-minute expiry, metadata-only audit, SQLite v2 migration and concurrency checks. Automated unit/HTTP tests PASS. **Real browser test BLOCKED** by Chromium administrator network policy; broader model-driven tools NOT IMPLEMENTED | Independent security review and on-device browser UAT; design next isolated tool |
| REQ-010 remote access | NOT STARTED | Loopback only | Plan approved VPN and remote client |
| REQ-011 ICF knowledge/integrations | NOT STARTED | No production data or vendor tokens accessed | Select sandbox workflow |
| REQ-012 Impact observer | NOT STARTED | Not collecting activity | Privacy/consent design |
| REQ-013 Windows `.exe` | BLOCKED | Build recipe staged; Windows runner/build/install NOT RUN | Verify on Windows with explicit CI cost authorization |
| REQ-014 NUC benchmark | BLOCKED | NUC/Qwen not available here | NUC GPU/runtime measurements |

**Phase state:** 00/01/02 IN PROGRESS (blueprint written; owner cutline subject to review); 03/04 IN PROGRESS (source pilot implemented); 05 IN PROGRESS (local automated tests only); 06 BLOCKED (Windows package/release unverified); 07 NOT STARTED; 08 applicable addenda BLOCKED for real Windows/edge/agent; 09 IN PROGRESS (records maintained, release gate enforced).

**Next vertical slice:** Verify local model API with the *actual* loaded Qwen3.5 9B runner on the NUC; measure throughput/latency, and manually verify the action UI in a normal Windows Chromium/Edge browser. After these gates, expand narrowly reviewed tools under human approval (no model-controlled execution enabled). Do not configure remote access, send external messages or launch paid CI without explicit separate approval.

**N/A:** mobile-app store submission and subscriptions (neither is part of this pilot); browser-extension store review (native localhost app, not browser extension).

## Windows EXE pilot evidence — 2026-11-19 UTC

- **VERIFIED CI PILOT BUILD ONLY:** Standard Windows runner success (run `44469707466`), 10,371,842-byte AMD64 PE executable and matching SHA-256, source commit `f09d43bebbae1eb455da989a51c038813ec32ff3` on dedicated build branch. Source socket fix is now being ported to `main`. The executable is **unsigned, non-installer, and not a public release**.
- `REQ-013`: **IN PROGRESS** (CI build and localhost startup smoke verified; clean Windows UAT and install/uninstall N/A for this portable-exe pilot; installer itself remains NOT STARTED). Do not describe the complete Windows release as ready.
- Remaining gates: owner double-click browser/enrollment/action testing, independent Defender/SmartScreen observation, real Qwen/NUC testing, broader agent controls, protected multiuser remote access. No new paid dependencies; public standard runner usage is free per GitHub billing documentation.

## 2026-11-20 HST — owner-approved final launch scope

Mandatory checkpoint FP-01–FP-08: [Five-Pillar Launch Gate](FIVE_PILLAR_LAUNCH_GATE.md). Brain, Shield, Decoy, Secured Pathway and Bouncer are locked. **Final integrated launch NO-GO; all five pillar acceptance tests NOT RUN.** Hardware/account setup and integration pending. Existing pilot evidence unchanged. Dedicated RAID/DAS and UPS deferred; minimal pCloud recovery and restore verification required. Next: verify target device capabilities and account types, implement and test isolated integration slices.
