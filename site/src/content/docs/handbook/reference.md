---
title: Reference
description: API stability contract, database guarantees, AI advisory model, configuration, and security posture.
sidebar:
  order: 4
---

This page is the technical reference for Payroll Engine. It covers the public API stability contract, database-level guarantees, the AI advisory model, configuration, and the security posture.

## API stability

Payroll Engine follows a strict stability contract. The public API surface is defined in `docs/public_api.md` and includes:

### Stable (will not break without a major version bump)

- The `PSP` facade class and all its public methods
- `PSPConfig` and all nested config dataclasses
- All result types returned by facade methods
- The `is_new` idempotency pattern
- Domain event types and their payload schemas
- CLI commands and their flags

### Internal (may change at any time)

- Individual service classes (`LedgerService`, `FundingGateService`, etc.)
- Repository implementations
- Database model classes
- Internal utility functions

:::caution
Do not import from internal modules directly. Use the `PSP` facade as the sole integration point. If you need something that is not exposed through the facade, open an issue — it may indicate a missing public API.
:::

## Database guarantees

The following invariants are enforced at the database level, not just in application code. They hold even if you bypass the facade and write SQL directly.

| Guarantee | Enforcement mechanism |
|-----------|----------------------|
| Money is always positive | `CHECK (amount > 0)` on all monetary columns |
| No self-transfers | `CHECK (debit_account_id != credit_account_id)` |
| Ledger is append-only | `BEFORE UPDATE` and `BEFORE DELETE` triggers reject mutations |
| Status only moves forward | Trigger validates allowed transitions |
| Events are immutable | Schema versioning enforced in CI |
| Idempotency keys are unique | `UNIQUE (tenant_id, idempotency_key)` per table |

### Schema verification

Run `psp schema-check` to verify all constraints are in place:

```bash
psp schema-check --database-url "$DATABASE_URL"
```

This checks every trigger, constraint, and index listed above. If anything is missing, the output tells you exactly what to add.

## AI advisory model

Payroll Engine includes optional AI features (installed via `pip install payroll-engine[ai]`). The AI model is **advisory-only** — it can analyze, score, and suggest, but it can never move money or write ledger entries.

### What AI can do

- **Risk scoring** — score a payroll batch for anomalies before commit
- **Return analysis** — classify return patterns and suggest process improvements
- **Runbook suggestions** — recommend operational actions based on event history

### What AI cannot do

- Create, modify, or delete ledger entries
- Approve or reject funding gate decisions
- Submit, cancel, or reverse payments
- Modify account balances or reservations

This is an architectural constraint, not a configuration option. The AI module has read-only access to the data layer. There is no code path from AI output to money movement.

### Disabling AI entirely

If you install only `payroll-engine` (no `[ai]` extra), the AI module is never loaded. The facade methods that accept AI parameters gracefully degrade to no-ops. There is no performance penalty for having AI absent.

## Configuration reference

### PSPConfig

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `tenant_id` | UUID | yes | Tenant isolation key |
| `legal_entity_id` | UUID | yes | Legal entity for compliance |
| `ledger` | LedgerConfig | yes | Ledger behavior |
| `funding_gate` | FundingGateConfig | yes | Gate configuration |
| `providers` | list[ProviderConfig] | yes | Payment rail providers |
| `event_store` | EventStoreConfig | no | Event store settings |

### LedgerConfig

| Field | Default | Purpose |
|-------|---------|---------|
| `require_balanced_entries` | `True` | Every debit must have a matching credit |

### FundingGateConfig

| Field | Default | Purpose |
|-------|---------|---------|
| `commit_gate_enabled` | `True` | Run the commit gate on batch submission |
| `pay_gate_enabled` | `True` | Run the pay gate before payment execution |
| `shortfall_policy` | `"hard_fail"` | Commit gate behavior on insufficient funds |

:::caution
Setting `pay_gate_enabled=False` is rejected in production. The facade checks and raises `ConfigurationError` if you attempt it outside test environments.
:::

### ProviderConfig

| Field | Purpose |
|-------|---------|
| `name` | Provider identifier (e.g., `"ach"`, `"fednow"`) |
| `rail` | Payment rail type |
| `credentials` | Provider-specific authentication |

## Error contract

All errors follow a structured shape:

```python
{
    "code": "FUNDING_INSUFFICIENT",
    "message": "Commit gate failed: available $500.00, required $1,200.00",
    "hint": "Fund the account or reduce the batch amount",
    "cause": None,
    "retryable": False
}
```

Error codes are namespaced and stable once released:

| Prefix | Category |
|--------|----------|
| `IO_` | Database or network I/O failures |
| `CONFIG_` | Configuration errors |
| `FUNDING_` | Funding gate failures |
| `PAYMENT_` | Payment submission errors |
| `SETTLEMENT_` | Settlement processing errors |
| `INPUT_` | Invalid input data |
| `STATE_` | Invalid state transition |

### CLI exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User error (bad input, missing config) |
| 2 | Runtime error (database down, provider unreachable) |
| 3 | Partial success (some operations succeeded, some failed) |

## Security posture

### Threat model

The full threat model is documented in `docs/threat_model.md` using STRIDE methodology. Key mitigations:

- **Spoofing** — Tenant isolation at the database level. Every query includes `tenant_id` in the WHERE clause.
- **Tampering** — Append-only ledger with database triggers. No application code can bypass the constraints.
- **Repudiation** — Immutable domain events with timestamps and actor attribution.
- **Information disclosure** — No secrets in logs, no stack traces in production error responses, API key hashing in audit logs.
- **Denial of service** — Idempotency prevents duplicate processing. Rate limiting on CLI and API endpoints.
- **Elevation of privilege** — AI module has read-only data access. No code path from advisory output to money movement.

### What Payroll Engine does not do

These are documented in `docs/non_goals.md`:

- Does not provide a UI or API server (it is a library)
- Does not manage user authentication or authorization
- Does not handle tax calculations or withholding
- Does not provide payroll scheduling or calendar management
- Does not store employee PII beyond account identifiers

## Documentation index

| Document | Location | Purpose |
|----------|----------|---------|
| `psp_invariants.md` | `docs/` | System invariants — what is guaranteed |
| `threat_model.md` | `docs/` | Security analysis (STRIDE) |
| `public_api.md` | `docs/` | API stability contract |
| `idempotency.md` | `docs/` | Idempotency patterns |
| `adoption_kit.md` | `docs/` | Evaluation and embedding guide |
| `non_goals.md` | `docs/` | What PSP explicitly does not do |
