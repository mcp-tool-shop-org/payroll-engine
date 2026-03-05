---
title: Usage
description: Library integration via the PSP facade, CLI tools for operations, and testing strategies.
sidebar:
  order: 2
---

Payroll Engine is a library, not a service. You embed it inside your application and interact through the PSP facade — a single entry point that enforces all invariants internally.

## The PSP facade

The facade is the **only blessed integration path**. Do not import internal services directly — their interfaces may change without notice.

```python
from payroll_engine.psp import PSP, PSPConfig
from payroll_engine.psp.config import (
    LedgerConfig,
    FundingGateConfig,
    ProviderConfig,
    EventStoreConfig,
)

config = PSPConfig(
    tenant_id=tenant_id,
    legal_entity_id=legal_entity_id,
    ledger=LedgerConfig(require_balanced_entries=True),
    funding_gate=FundingGateConfig(
        commit_gate_enabled=True,
        pay_gate_enabled=True,  # NEVER set to False in production
    ),
    providers=[
        ProviderConfig(name="ach", rail="ach", credentials={...}),
    ],
    event_store=EventStoreConfig(),
)

psp = PSP(session=db_session, config=config)
```

:::caution
Configuration is explicit — there are no magic defaults, no implicit environment variables, and no hidden globals. Every setting that affects money movement must be passed in deliberately.
:::

### Committing payroll

The commit step runs the **commit gate** (do we have the money to promise these payments?) and creates fund reservations.

```python
commit_result = psp.commit_payroll_batch(batch)

# commit_result.is_new == True  → newly committed
# commit_result.is_new == False → idempotent duplicate (same reservation returned)
# commit_result.reservation_ids → list of reservation UUIDs
# commit_result.total_reserved  → Decimal total held
```

### Executing payments

The execute step runs the **pay gate** (do we still have the money right now?) and submits payment instructions to the configured rail provider.

```python
execute_result = psp.execute_payments(
    tenant_id=tenant_id,
    legal_entity_id=legal_entity_id,
    batch_id=batch_id,
    scheduled_date=date.today(),
)

# execute_result.submitted_count → number sent to provider
# execute_result.failed_count    → number that failed the pay gate
# execute_result.instructions    → per-instruction results
```

### Ingesting settlement feeds

Settlement is when the bank confirms what actually happened. Until you ingest the settlement feed, a payment is in-flight — not confirmed.

```python
ingest_result = psp.ingest_settlement_feed(
    tenant_id=tenant_id,
    bank_account_id=bank_account_id,
    provider_name="ach",
    records=settlement_records,
)

# ingest_result.matched_count   → successfully matched to instructions
# ingest_result.unmatched_count → records with no matching instruction
# ingest_result.duplicate_count → already-processed records (idempotent)
```

Unmatched settlements are flagged for manual review. The system never auto-credits an account from an unmatched record.

### Querying balances

```python
balance = psp.get_balance(tenant_id=tenant_id, account_id=account_id)

# balance.total     → all credits minus all debits
# balance.reserved  → funds held by active reservations
# balance.available → total minus reserved (what can be disbursed)
# balance.as_of     → timestamp of the computation
```

### Replaying events

Every state change in the system emits a domain event. You can replay them for debugging, auditing, or rebuilding state.

```python
for event in psp.replay_events(
    tenant_id=tenant_id,
    after=datetime(2025, 1, 1),
    event_types=["PaymentSettled", "PaymentReturned"],
    limit=500,
):
    print(f"{event.timestamp} {event.event_type}: {event.payload}")
```

## Idempotency

Every operation that creates or modifies data returns a result with an `is_new` flag. This is critical for safe retries.

```python
result = psp.commit_payroll_batch(batch)

if result.is_new:
    # First call — reservation was created
    notify_downstream(result.reservation_ids)
else:
    # Duplicate call — same reservation returned, no side effects
    log.info(f"Duplicate commit, returning existing {result.batch_id}")
```

The pattern applies everywhere: ledger postings, payment instructions, settlement records, and domain events. A duplicate is not an error — it is expected behavior in a system that handles retries correctly.

:::tip
Use stable, deterministic idempotency keys that encode the logical operation:
```python
f"commit:{batch_id}"
f"payment:{batch_id}:{employee_id}"
f"settlement:{provider}:{trace_id}"
```
Never use random UUIDs as idempotency keys — that defeats the purpose.
:::

## CLI tools

Payroll Engine includes a CLI for operational tasks. Run `psp --help` for the full list.

### Health and diagnostics

```bash
# Check database connectivity and component health
psp health
psp health --component db
psp health --component providers

# Output metrics in JSON or Prometheus format
psp metrics --format json
```

### Schema verification

```bash
# Verify all database constraints are in place
psp schema-check --database-url $DATABASE_URL
```

This catches missing triggers, constraints, or indexes that could compromise system invariants.

### Event operations

```bash
# Replay events for a tenant (useful for debugging)
psp replay-events --tenant-id $TENANT --since "2025-01-01"

# Dry-run replay (shows what would happen, no side effects)
psp replay-events --tenant-id $TENANT --since "2025-01-01" --dry-run

# Export events to JSONL for external audit
psp export-events --tenant-id $TENANT --output events.jsonl

# List active event subscriptions
psp subscriptions --list
```

### Balance queries

```bash
# Query an account balance
psp balance --tenant-id $TENANT --account-id $ACCOUNT
```

## Testing

### Running the test suite

```bash
# All unit tests
make test

# PSP-specific tests with database
make test-psp

# Fast mode (stop on first failure)
make test-fast

# With coverage report
make test-cov
```

### Red team tests

The repository includes constraint verification tests that deliberately attempt to violate system invariants — negative amounts, self-transfers, backward status transitions, and direct ledger mutations.

```bash
pytest tests/psp/test_red_team_scenarios.py -v
```

These tests prove the constraints hold at the database level, not just the application level. If a red team test fails, it means a critical invariant is unprotected.

### Testing idempotency

Every idempotent operation should be tested with the "call twice, verify no duplication" pattern:

```python
def test_commit_is_idempotent():
    result1 = psp.commit_payroll_batch(batch)
    assert result1.is_new is True

    result2 = psp.commit_payroll_batch(batch)
    assert result2.is_new is False
    assert result2.batch_id == result1.batch_id
```

## Next steps

To understand **why** the system is designed this way, read [Concepts](/payroll-engine/handbook/concepts/).
