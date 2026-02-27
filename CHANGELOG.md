# Changelog

All notable changes to this project are documented here.

This project follows:
- Semantic Versioning as defined in `docs/compat.md`
- Forward-only database migrations
- Additive-only event evolution unless explicitly versioned (V2)

**Financial correctness and auditability take precedence over convenience.**

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

---

## [1.0.0] - 2026-02-27

### Changed
- Promoted to v1.0.0 — production-stable release
- Shipcheck audit pass: SECURITY.md, threat model, structured errors, operator docs

### Database / Migration Notes
- No migration changes

### Event Compatibility
- No event changes

### Operational Notes
- No operational changes

---

## [0.2.1] - 2026-02-22

### Fixed
- **Release workflow**: SBOM generation updated for cyclonedx-bom v7 CLI (`--format` → `--of`)

---

## [0.2.0] - 2026-02-22

**Database constraint overhaul — all 8 CI jobs green.**

### Fixed

- **Migration 206 CHECK constraints** aligned with production code values: added all entry types, purposes, payee types, and statuses used by 201/202 services
- **Dual-constraint conflict** resolved: original inline CHECK constraints from `CREATE TABLE` in 201/202 are now explicitly dropped before 206 replaces them with named constraints
- **Status transition triggers** updated to allow all valid paths (e.g. `submitted → settled` for instant payment rails, `created → settled` for settlement events)
- **Ambiguous column reference** in reconciliation SQL: `psp_ledger_entry_id` qualified with table alias in `_handle_status_change` JOIN query (both sync and async)
- **Payroll stub migration** (200) updated with missing columns (`period_start`, `period_end`) and all stub tables needed by integration tests
- **Double-reversal test** fixed to validate trigger behavior correctly (BEFORE INSERT trigger fires before ON CONFLICT)
- **PSP facade** rewritten to match actual service APIs (57 pyright errors resolved)
- **Type safety** restored: Decimal arithmetic, rowcount guards, None checks across all services

### Database / Migration Notes
- Migration 206 substantially reworked — drops all original inline constraints before adding named replacements
- Migration 200 adds `period_start` and `period_end` columns to `pay_run` stub
- No new tables added; existing constraint definitions expanded

### Event Compatibility
- No event changes

### Operational Notes
- CI expanded to 8 jobs: core-only, lint, unit tests, DB integration, migration lint, constraint tests, event compat, demo smoke test
- All red team / constraint tests now execute without skips

---

## [0.1.0] - 2025-01-25

**Initial Public Release**

### Added

#### Core PSP
- **PSP Facade** (`src/payroll_engine/psp/psp.py`) - Single entry point for all PSP operations
- **Ledger Service** - Append-only double-entry ledger with balance tracking
- **Funding Gate** - Two-gate model (commit gate + pay gate) preventing unfunded payments
- **Payment Service** - ACH and FedNow rail abstraction with provider protocol
- **Settlement Service** - Bank feed ingestion and reconciliation
- **Liability Service** - Return classification and recovery path assignment

#### Configuration
- **PSPConfig** - Explicit configuration objects (no env vars, no magic)
- **LedgerConfig**, **FundingGateConfig**, **ProviderConfig**, **EventStoreConfig**
- `validate_production_config()` helper for deployment safety checks

#### Domain Events
- **Event Store** - Append-only event log with replay capability
- **Event Subscriptions** - Cursor-based consumption for integrations
- 14 stable event types: `PaymentInstructionCreated`, `PaymentSubmitted`, `PaymentSettled`, `PaymentReturned`, etc.
- Event schema versioning with CI enforcement

#### Database
- PostgreSQL schema with 11 core tables
- DB constraints enforcing impossible states:
  - `CHECK (amount > 0)` on all money columns
  - `CHECK (debit_account_id <> credit_account_id)`
  - Status transition triggers
  - Reversal integrity constraints
- Migration system with forward-only guarantee

#### CLI Tools
- `psp health` - System health check
- `psp schema-check` - Verify DB constraints are applied
- `psp balance` - Query account balances
- `psp replay-events` - Event replay for debugging
- `psp export-events` - Audit export to JSONL
- `psp metrics` - Prometheus/JSON metrics export
- `psp subscriptions` - Manage event subscriptions

#### Observability
- **MetricsCollector** - Payment counts, settlement rates, latencies
- **DailyHealthSummary** - Automated health report generation
- Structured logging patterns

#### Documentation
- `docs/public_api.md` - Public API contract
- `docs/compat.md` - Versioning and compatibility rules
- `docs/invariants.md` - System guarantees
- `docs/idempotency.md` - Idempotency patterns
- `docs/threat_model.md` - Security analysis
- `docs/non_goals.md` - Explicit non-goals
- `docs/adoption_kit.md` - Evaluation and embedding guide
- `docs/upgrading.md` - Upgrade playbook
- `docs/runbooks/` - Operational procedures
- `docs/recipes/` - Integration examples

#### Testing
- Unit tests for all services
- Integration tests with real PostgreSQL
- Red team tests verifying DB constraints work
- Property-based tests for invariants (hypothesis)
- Event schema compatibility checker

#### DevOps
- `docker-compose.yml` for local development
- `Makefile` with one-command operations
- GitHub Actions CI with 8 jobs:
  - Lint & type check
  - Unit tests
  - DB integration tests
  - Migration linter
  - Constraint tests
  - Event compatibility check
  - Demo smoke test

#### Example
- `examples/psp_minimal/` - Library-first demonstration
- Shows full lifecycle: commit → execute → settle → return → liability

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- Tenant isolation enforced at DB level
- Webhook signature verification pattern
- No credentials in code (explicit config only)
- Audit trail via immutable events

### Database / Migration Notes
- Requires applying all migrations in `psp_build_pack_v2/psp_build_pack/migrations/` (forward-only)
- Includes append-only triggers and constraint enforcement
- Migration files: `201_ledger_tables.sql` through `206_impossible_state_constraints.sql`

### Event Compatibility
- All events are version 1
- Payloads are additive-only going forward
- Breaking changes will introduce new event names or V2 suffixes
- Baseline schema: `event_schema.json`

### Operational Notes
- This is a **library**, not a service
- No HTTP endpoints, workers, or schedulers are included
- Adopters are responsible for database lifecycle and backups
- Verify schema after migration: `psp schema-check --database-url $DATABASE_URL`

---

## Release Notes Template

Every future release must include:

```markdown
### Database / Migration Notes
- Migrations added: `NNN_description.sql`
- Constraints added: ...
- (or "No migration changes")

### Event Compatibility
- New events: ...
- New fields: ... (additive-only)
- (or "No event changes")

### Operational Notes
- Runbook updates: ...
- CLI changes: ...
- (or "No operational changes")
```

---

## Release Process

See [RELEASING.md](RELEASING.md) for the full release checklist.

Quick steps:
1. Update version in `pyproject.toml`
2. Update this CHANGELOG (move Unreleased to new version)
3. Run verification: `make test && psp schema-check`
4. Create git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. Push tag: `git push origin vX.Y.Z`
6. CI builds and publishes to PyPI

## Versioning

- **MAJOR**: Breaking changes to public API (see `docs/public_api.md`)
- **MINOR**: New features, additive changes
- **PATCH**: Bug fixes, documentation

[Unreleased]: https://github.com/mcp-tool-shop-org/payroll-engine/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/mcp-tool-shop-org/payroll-engine/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/mcp-tool-shop-org/payroll-engine/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mcp-tool-shop-org/payroll-engine/releases/tag/v0.1.0
