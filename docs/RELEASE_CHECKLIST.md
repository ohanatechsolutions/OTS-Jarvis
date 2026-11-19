# OTS Jarvis — Windows Release Checklist

**Decision: NO-GO.** Local action approvals pass automated checks, but actual Chromium UI testing was blocked by environment policy and the NUC/Windows tests remain open. Source pilot is not a verified Windows product. No signed binary or approved release publication exists. No CI minutes/charges authorized by this record.

## Pre-release steps

- [ ] Source commit and locked build dependencies reviewed. No secret / high severity dependency findings.
- [ ] `python -m unittest discover -s tests -v` passes on Windows x64 and Linux; runtime model and security negative tests run.
- [ ] On Windows x64, run `./scripts/build_windows.ps1` after reviewing dependencies and license. This creates an **unsigned** PyInstaller console executable if successful.
- [ ] Verify file starts with Windows PE `MZ` and is x64; verify executable launches, binds only localhost, opens setup/login and persists state.
- [ ] Test clean Windows 11 standard-user install/run/uninstall, Model offline response, and model online request on actual NUC.
- [ ] SHA-256 checksum saved and independently rechecked after copy/download; check Microsoft Defender/SmartScreen behavior, do not suggest disabling protections.
- [ ] Verify app assets and Python runtime are packaged. Document how Windows firewall rules and per-user data retention work.
- [ ] Check uninstall/rollback and backup restore; confirm no production user data loss.
- [ ] Confirm MFA/employee/remote/agent functionality is *not advertised* as supported until implemented.
- [ ] Owner reviews privacy, license, threat model, cost and UAT evidence. Approve release/version/tag/channel explicitly.
- [ ] Only after approval, publish artifact and verify actual link resolves on a separate Windows machine.

## Local build recipe (not run on Windows in this session)

PowerShell from project root:

```powershell
python -m pip install --upgrade pip
python -m pip install "pyinstaller==6.15.0"
python -m unittest discover -s tests -v
./scripts/build_windows.ps1
Get-FileHash dist/OTS-Jarvis.exe -Algorithm SHA256
```

**Note:** Pin/toolchain chosen for repeatability, not a claim of Windows compatibility; validate availability and license before use. PyInstaller is a free open-source tool, but runner minutes, signing certificate and hardware may cost money. The workflow in `.github/workflows/windows-build.yml` is **manual only** and cannot automatically publish a release. It must not be run without confirming GitHub Actions budget/usage authorization.

**Version:** Source `0.1.0a2` development; no Git tag. **Artifact SHA:** N/A — no executable produced here. **Human release owner:** Ohana Tech Solutions, signoff pending. **Rollback:** retain a verified prior installer and back up per-user DB before any upgrade; clean install and restore procedure yet to be validated.
