# Changelog

## [Unreleased] — v0.1.0a2 action-gateway development

- Locked the five-pillar deployment architecture and mandatory final integrated launch checkpoint (FP-01–FP-08); documentation only, not deployed or verified.

- Added a SQLite-backed, local-only supervised `save_note` action: explicit proposal, preview, approval, atomic execution, cancel, undo and pause/resume controls.
- Added redacted metadata-only action audit history with a 90-day terminal-event retention policy; active notes remain undoable until removed.
- Added schema v1→v2 migration, bounded pending actions/notes, duplicate execution prevention and restart recovery for stranded model tasks; duplicate-port launch now fails before changing persisted state.
- Added end-to-end HTTP approval tests, expiration/authorization tests, concurrency, migration and rollback tests; browser automation provided but browser execution remains environment-blocked.

## [v0.1.0a1] — Local pilot baseline

- Added loopback-only Python assistant UI and server.
- Added one-time admin enrollment, PBKDF2 password hashes and revocable local sessions.
- Added local model adapter, deterministic AUTO output-depth routing and SQLite history.
- Added input, origin, host, response-size and concurrency controls with negative tests.
- Added project blueprint, evidence and release-gate records.
- Windows installer, remote access, agent tools and production Qwen performance remain unverified/out of pilot scope.
