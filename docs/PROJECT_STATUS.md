# OTS Jarvis — Project Status

**Updated:** 2026-11-18 HST. **Owner:** Ohana Tech Solutions. **Baseline:** Newly established source pilot; earlier v0.2.0 installer ZIP and Git bundle exist in Library but raw bytes were unavailable to the active workspace. This code is a distinct reconstructed pilot baseline, not an asserted import of that historical code.

**GitHub:** `ohanatechsolutions/OTS-Jarvis`; default branch `main`. **Source test environment:** Linux, Python 3.13.5. **Windows pre-release:** NO-GO.

| Requirement | Status | Evidence/limitation | Next |
|---|---|---|---|
| REQ-001 local admin enrollment | IN PROGRESS | Automated store+HTTP tests PASS; manual browser UAT not run | Test on clean Windows profile |
| REQ-002 login/session/logout | IN PROGRESS | Automated HTTP tests PASS; Windows browser UAT pending | Manual auth/expiry tests |
| REQ-003 local AI inference adapter | IN PROGRESS | Contract tests PASS against fake localhost runner; **real Qwen NOT RUN** | Configure local runner and benchmark |
| REQ-004 local task history | IN PROGRESS | API/store tests PASS; purge at restart only | Verify restart/retention behavior |
| REQ-005 local URL security | IN PROGRESS | Negative URL/Origin/Host checks PASS | Independent security review |
| REQ-006 UI/accessibility | IN PROGRESS | HTML/CSS/JS implemented; JS syntax checked | Manual keyboard/mobile/screen-reader UAT |
| REQ-007 deterministic AUTO routing | IN PROGRESS | Unit/integration PASS | Confirm UX with owner on real model |
| REQ-008 multiuser/MFA | NOT STARTED | Beyond single-admin pilot | Design authentication and device enrollment |
| REQ-009 agent tool approval | NOT STARTED | No executable agent tools present | Implement threat model/permission gateway |
| REQ-010 remote access | NOT STARTED | Loopback only | Plan approved VPN and remote client |
| REQ-011 ICF knowledge/integrations | NOT STARTED | No production data or vendor tokens accessed | Select sandbox workflow |
| REQ-012 Impact observer | NOT STARTED | Not collecting activity | Privacy/consent design |
| REQ-013 Windows `.exe` | BLOCKED | Build recipe staged; Windows runner/build/install NOT RUN | Verify on Windows with explicit CI cost authorization |
| REQ-014 NUC benchmark | BLOCKED | NUC/Qwen not available here | NUC GPU/runtime measurements |

**Phase state:** 00/01/02 IN PROGRESS (blueprint written; owner cutline subject to review); 03/04 IN PROGRESS (source pilot implemented); 05 IN PROGRESS (local automated tests only); 06 BLOCKED (Windows package/release unverified); 07 NOT STARTED; 08 applicable addenda BLOCKED for real Windows/edge/agent; 09 IN PROGRESS (records maintained, release gate enforced).

**Next vertical slice:** Test the API with the *actual* loaded Qwen3.5 9B runner on the NUC; measure throughput, latency and model path, then implement explicit task planning/approval and cancellation before adding any agent action tools. Do not configure remote access, send external messages or launch paid CI without explicit separate approval.

**N/A:** mobile-app store submission and subscriptions (neither is part of this pilot); browser-extension store review (native localhost app, not browser extension).
