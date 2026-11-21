# OTS Jarvis — Five-Pillar Defense Architecture and Final Launch Gate

**Decision:** Owner-approved, 2026-11-20 HST. **Scope:** Mandatory for final integrated product launch; not required to run isolated localhost development previews. **Gate: NO-GO — integration and acceptance evidence pending.**

| ID | Locked pillar | Component | Required acceptance evidence |
|---|---|---|---|
| FP-01 | Brain | Intel NUC 12 Enthusiast / Serpent Canyon, i7-12700H, Arc A770M 16 GB VRAM, 32 GB RAM, 1 TB SSD | Actual Windows/Jarvis/OTS Security Suite installation, real local Qwen3.5 9B inference, measured throughput/latency/thermal and memory behavior, simultaneous staff workload, restart and recovery |
| FP-02 | Shield | Firewalla Orange | Confirm exact SKU and supported routing/VLAN/VPN features; verify default-deny inter-zone policy, approved remote access, blocked unauthorized ingress, alerting, recovery and no direct public exposure |
| FP-03 | Decoy | Raspberry Pi 3 B+ running OpenCanary | Isolated decoy VLAN, no access to privileged systems or real data, authorized simulated decoy interaction produces authenticated sanitized incident alert, replay/duplicate handling, fail-safe when sensor offline |
| FP-04 | Secured Pathway | Managed VLAN-capable LAN switch | Confirm 802.1Q compatibility, management restrictions, port/VLAN assignment, allowed flow tests and denied cross-zone/pivot tests; no reliance on switching alone for access control |
| FP-05 | Bouncer | Zero-trust identity and application authorization | Inventory account types and native permissions; separate admin/recovery identities, phishing-resistant MFA, approved devices, least privilege, backend role/resource checks, independent alerts, high-risk approvals and tested session/token revocation after simulated employee compromise |

## Integration design

Internet/ISP -> Shield -> Secured Pathway -> Brain and isolated Decoy. Bouncer applies across cloud and local identity boundaries (Google, Squarespace, Jarvis, TanDM and privileged accounts); it is not an inline appliance. Google/Squarespace native controls remain authoritative. OpenCanary is the honeypot; OpenCanopy is an optional dashboard, not required. OTS Security Suite provides central incident visibility on Brain; cross-repository work must be reconciled with its incident-center and identity-security specifications. Previous names Barbed Fence, Booby Trap and Watchdog are superseded by Shield, Decoy and Bouncer.

## Final product checkpoint — all required

- [ ] FP-01 Brain verified on actual target hardware.
- [ ] FP-02 Shield configured and tested.
- [ ] FP-03 Decoy configured, isolated and end-to-end alert verified.
- [ ] FP-04 Secured Pathway configured and negative isolation tests passed.
- [ ] FP-05 Bouncer implemented and account-takeover drill passed, with platform-specific limitations recorded and owner accepted.
- [ ] FP-06 Integrated scenario: authorized staff access and normal workloads succeed; simulated unauthorized network and identity access denied; decoy alerts reach incident center; approved revocation/containment and recovery work. Verify component outage/reboot, independent admin access, audit/privacy and rollback.
- [ ] FP-07 Minimal encrypted versioned recovery of irreplaceable local state and critical records using existing pCloud capacity, with restore test and independent credentials. No dedicated RAID/DAS or added cloud storage required at launch; UPS deferred. Ordinary sync is not a backup. Test power-loss recovery despite no UPS.
- [ ] FP-08 Existing Windows packaging, security review, licensing/cost, user acceptance and owner go/no-go gates passed against exact release artifact and hardware/software versions.

All FP checkpoints are **NOT VERIFIED**; physical integration is **BLOCKED pending access to actual equipment and authorized account configuration**. No purchases, deployments, account changes, paid services, port forwarding or automated containment authorized by this decision. No guaranteed complete protection from legitimate-access data theft. No release can be described as the final integrated product until every applicable checkpoint passes with evidence and owner signoff. Preserve earlier pilot evidence as pilot-only; no test result is implied by this documentation change.

Evidence for each gate must record source commit/artifact hash, device model/firmware, sanitized configuration, test procedure, actual result, date and reviewer. Store evidence without real credentials, production network identifiers or employee/customer data. Applicable OTS framework phases 00–07, 09 and addenda 08.01, 08.05–08.08; payments/store submission N/A for internal deployment.
