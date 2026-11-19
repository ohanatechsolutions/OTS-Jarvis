# Jarvis — Tool Stack and Pre-Hardware Integration Plan

**Status:** Integration plan, not installed-software evidence. **Updated:** 2026-11-19 HST. **Source:** Prior OTS Jarvis 45-tool evaluation and follow-up shortlist, combined with current repo inspection. The verbatim 45-item numbered inventory was not recoverable here; **do not label this a full item-by-item 45-tool audit**.

## Confirmed constraints

- 100% free-forever adopted runtime (open source or permanent self-hosted license); no paid API, hosted AI, subscription, usage metering, or cloud dependency.
- Local-first/private; all external actions require least-privilege user approval, audit, revocation and stop controls. Production user data may not be sent to external AI or trial services.
- Planned Intel NUC 12 Enthusiast i7-12700H, Intel Arc A770M 16 GB, 32 GB RAM, 1 TB SSD. Preferred Qwen3.5 9B. **Real performance and GPU support not yet measured**.
- Current Windows pilot remains a one-admin loopback application. Not a distributed multiuser agent.

## Final selected shortlist — exactly 10

**Decision origin:** Latest 45-plus-tool evaluation narrowed to **10 selected candidates** (not 10 already-installed dependencies). This section is the authoritative selected set. Runtime prerequisites like Qwen3.5 9B, a local inference runner, SQLite, Playwright and WireGuard are *supporting infrastructure*, not replacements for or additions to these 10 decisions.

| # | Selected tool | Intended role | Integration priority | Verified in Jarvis repo? |
|---|---|---|---|---|
| 1 | **Nous Research Hermes Agent** | Local-first agent/controller with explicit Jarvis-side approval policy | P1, after local runner contract | **No** — model/tool compatibility and security gates |
| 2 | **Scrapling** | Permitted read-only website extraction | P2, after knowledge pipeline | **No** — license/website rules and isolation review |
| 3 | **Hex** | Optional local speech dictation interface | P3 | **No** — evaluate offline requirements and correct upstream project |
| 4 | **NVIDIA OpenShell** | Sandboxed agent/worker execution | P1 architecture; NUC/Linux validation later | **No** — Linux environment required for actual evaluation |
| 5 | **CC Safety Net** | Additional command execution guard | P2 | **No** — compatibility and deny-policy testing needed |
| 6 | **TruffleHog** | Source/repository secret scanning | P0 developer security tooling | **No** — scan evidence not yet collected |
| 7 | **NVIDIA SkillSpector** | Vet third-party agent skills prior to installation | P1 before imported skills | **No** — prevent external/cloud analysis by default |
| 8 | **Pangolin Community Edition** | Conditional remote access option | P3 after MFA/device security | **No** — verify CE licensing and network exposure; WireGuard remains simpler baseline |
| 9 | **GitHub Spec Kit** | Development-time spec workflow, not shipped in Jarvis | P2 optional | **No** — current five-source framework already governs work |
| 10 | **Unsloth** | Optional local model fine-tuning if evaluations justify it | P4 | **No** — unnecessary for initial AI/automation milestone |

**Selection vs deployment:** A tool may be *selected* but **not ready to install** on the current Windows pilot. OpenShell, Pangolin and Unsloth are explicitly environment- or phase-dependent. The preferred local model and existing Jarvis authorization gateway remain prerequisites, and Hermes is conditional on actual hardware/model compatibility.

**Not members of the selected ten:** Jan/Qwen3.5 (model runtime), Playwright (browser adapter), WireGuard (network transport), SQLite (storage), restic (backup), Semgrep/OSV (supplementary CI). These may still be useful supporting components; do not present them as extra adopted items from the original ten. Paid hosted platforms remain excluded.

**Immediate executable slice:** `I-001` authenticated loopback Jan adapter with model discovery, status/test connection control and negative security tests. It can be coded and contract-tested before NUC arrival, with a real model smoke test deferred. Then introduce Hermes behind the *existing Jarvis approval boundary*, without granting arbitrary OS/network access.

## Tools and integration disposition

| Layer | Preferred component | Disposition now | Why / integration gate |
|---|---|---|---|
| Local inference | Qwen3.5 9B + Jan local server initially | **CONNECT NEXT** | Existing loopback OpenAI-compatible adapter; add local-only API-key support, model discovery and real integration tests; runner availability/Intel GPU later |
| Model runtime alternative | llama.cpp/OpenVINO | **BENCHMARK LATER** | Evaluate on actual Arc GPU, avoid operating redundant inference servers |
| Agent brain | Nous Research Hermes Agent | **ADOPT CONDITIONALLY, NOT CONNECTED** | MIT self-hosted; integrate behind Jarvis policy gateway only after local model/tool compatibility and license review; disable built-in broad tools/cloud routes |
| Agent execution isolation | NVIDIA OpenShell | **ADOPT FOR LINUX EVALUATION, NOT CONNECTED** | Apache-2.0 sandbox with enforced policies; validate on NUC/Linux; no presumed native Windows sandbox compatibility |
| Browser automation | Playwright | **PREPARE ADAPTER** | Isolated browser worker and explicit site/action allowlists; draft-only/synthetic flows first |
| Web content extraction | Scrapling | **ADOPT FOR READ-ONLY APPROVED SITES, LATER** | Check BSD license/robots/website terms; not for bypassing protections or uncontrolled crawling |
| Local knowledge | SQLite + FTS for initial ICF documents | **BUILD NOW** | Reuse current SQLite; cite sources, version, access controls and deletion; no model or heavy DB prerequisite |
| Larger search / relational store | PostgreSQL + pgvector | **OPTIONAL LATER** | Only migrate if scale and measurements justify; avoid adding a second database immediately |
| Human approval / action ledger | Native Jarvis SQLite gateway | **PARTIAL, VERIFIED LOCAL NOTE ONLY** | Extend to drafts; approvals, audit, rollback, kill switch and connector permission scopes required |
| Staff identity | Authentik / OIDC | **DESIGN NOW, DEPLOY LATER** | Evaluate community-license scope, MFA and secure network model; remote service must not be public without hardening |
| Remote networking | WireGuard; Pangolin Community Edition optional | **DESIGN NOW, DEPLOY LATER** | WireGuard first for simple private tunnel; Pangolin CE is AGPLv3, avoid needing enterprise features; do not expose localhost web UI |
| Voice dictation | Hex or OpenWhispr, plus local speech tools | **DEFER, SELECT ONE** | Both are optional frontend alternatives, not both required; enforce offline transcription only |
| Local voice output | Kokoro TTS | **DEFER** | Optional, independent module |
| Backups | restic | **PLAN BEFORE PRODUCTION** | Encrypted local/offline backup, restore rehearsal and retention; software free but storage hardware may cost |
| Tool/code security | TruffleHog, Semgrep CE, OSV-Scanner | **USE IN CI AS APPLICABLE** | Source/dependency scan before importing code; report results accurately, no cloud secrets |
| Skill intake scanning | NVIDIA SkillSpector | **USE BEFORE EXTERNAL SKILLS** | Apache-2.0; disable LLM-provider analysis unless confirmed local, since default may transmit file contents |
| Command safety | CC Safety Net | **OPTIONAL SECOND LAYER** | MIT; confirm support for actual agent interfaces; not a substitute for sandbox/approvals |
| Project planning | GitHub Spec Kit | **OPTIONAL DEVELOPMENT TOOL** | MIT; complements existing 5-source framework, not a shipped dependency |
| Fine-tuning | Unsloth core | **LATER ONLY** | Apache-2.0 core; optional Studio AGPL; do not fine-tune before evaluation data and necessity demonstrated |
| Hosted alternatives | CodeRabbit, Aikido paid layers, Automater.ai, Composio hosted, Orgo, Weft, hosted Firecrawl, Wispr Flow | **EXCLUDE FROM $0 RUNTIME** | Freemium/paid/hosted constraints or overlap; do not assume consumer ChatGPT or other subscriptions include API credits |

**License gate:** Record exact upstream commit/version, license, optional transitive dependencies, and bundled/redistribution terms for each tool before vendoring, packaging or commercial resale. Pangolin CE AGPL obligations and Unsloth Studio AGPL require special review.

## What can be completed before arrival of the NUC

1. **I-001 Local runner contract:** implement a Jan-compatible endpoint adapter supporting a locally supplied API key from environment or protected user configuration (never logged or stored in SQLite); refuse non-loopback URLs; add authenticated/unauthenticated fake-local-runner tests, 401/offline/timeout tests, health and model discovery. Expose a simple 'Test local AI connection' screen. **Gate:** Windows end-to-end API tests, no network beyond loopback.
2. **I-002 Local knowledge base:** metadata/source-aware SQLite ingestion for explicitly selected non-sensitive TXT/MD/PDF-extracted text (PDF handling independently vetted), citation-based search and document delete/update; default deny external URLs. **Gate:** actual upload/query/delete/restart flows plus authorization/secret-leak tests; can test without NUC.
3. **I-003 Capability registry:** explicit signed/allowlisted adapter definitions, read-only vs draft vs external-side-effect policies, preview exact payload, admin approval and audit; all connectors initially disabled. **Gate:** malicious-model/tool outputs cannot run actions without server-side permission.
4. **I-004 Browser worker prototype:** isolated Playwright task with synthetic test site and screenshots; disable arbitrary web navigation and sending/posting. **Gate:** reproducible headless tests and cancellation.
5. **I-005 ICF business adapters:** Gmail/Sheets and ICF website read-only sandbox adapters; drafts only for outbound mail or TanDM. **Gate:** scope review, OAuth security, synthetic test accounts and explicit user authorization before any real account connection.
6. **I-006 Windows client install/update:** bundled native Windows pilot with settings, reliable stop/start, secure local profile storage, observable errors and backup. **Gate:** clean Windows UAT, installer/upgrade/uninstall and rollback testing.
7. **I-007 Multiuser security design:** role matrix (admin, employee), device approval, MFA, sessions/revocation, audit, VPN topology; do not enable until transport and identity are tested.

## Hardware-dependent tasks

- Install and benchmark real Qwen3.5 9B on intended NUC; compare Jan/llama.cpp/OpenVINO paths, 32 GB RAM and Intel Arc GPU behavior; track time-to-first-token, tokens/sec, peak RAM/VRAM, failure/recovery and 3-user contention.
- Deploy isolated Linux worker if OpenShell/Hermes require it; verify tool sandboxing and communication policy.
- Configure always-on service, network isolation, WireGuard access from approved devices, encrypted backups, disaster-recovery drill and power/thermal measurements.
- Validate actual ICF workflow on authorized accounts only after dry-runs and human approvals.

## Important current reality (inspection)

- Existing repo has a Python stdlib HTTP service, SQLite v2, protected admin UI, local OpenAI-compatible model adapter, and explicit local-note approval/undo. It does **not** contain Hermes, OpenShell, Jan installation, general browser tools, ingestion/search, Google connectors, employee auth, VPN, voice or monitoring.
- `JARVIS_MODEL_ENDPOINT` is loopback only. Current model adapter has no configured Jan authorization API-key support. Real model requests cannot be assumed working until tested.
- The verified unsigned Windows EXE pilot confirms Windows CI packaging and localhost startup, **not** integrated models or production readiness.
- No production credentials, paid endpoints, remote listeners, business data or actual vendor integrations have been configured by this plan.

## Acceptance and side-effect gates

- Development/imports in a sandbox and synthetic tests: permitted after dependency/license review; **no secret data, paid services or public exposure**.
- Account login/OAuth token collection, joining a business network, mailing/posting, website changes, broad desktop control, buying storage, deploy/release, remote firewall exposure: separate explicit owner approval.
- `N/A` for mobile app-store submission (not targeting native mobile distribution); `N/A` for training infrastructure until a real model quality gap is documented.
