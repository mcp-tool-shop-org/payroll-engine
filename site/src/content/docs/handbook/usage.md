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
from payroll_engine.psp import PSP
from payroll_engine.psp.providers.ach_stub import AchStubProvider

# The facade accepts an optional PSPConfig (from psp.psp, not psp.config)
# and a dict of named rail providers.
psp = PSP(
    session=db_session,
    providers={"ach": AchStubProvider()},
)

# For production, register real providers:
# psp.register_provider("ach", your_ach_provider)
```

The separate `PSPConfig` in `payroll_engine.psp.config` (with `LedgerConfig`, `FundingGateConfig`, `ProviderConfig`, `EventStoreConfig`) defines the configuration schema for your application's setup layer. The facade's own `PSPConfig` controls gate behavior and default rail selection at runtime.

:::caution
Configuration is explicit — there are no magic defaults, no implicit environment variables, and no hidden globals. Every setting that affects money movement must be passed in deliberately.
:::

### Committing payroll

The commit step runs the **commit gate** (do we have the money to promise these payments?) and creates fund reservations.

```python
from payroll_engine.psp.psp import PayrollBatch, PayrollItem

batch = PayrollBatch(
    batch_id=batch_id,
    tenant_id=tenant_id,
    legal_entity_id=legal_entity_id,
    pay_period_id=pay_period_id,
    funding_account_id=funding_account_id,
    items=[PayrollItem(payee_type="employee", payee_ref_id=emp_id, amount=amount, purpose="employee_net")],
    effective_date=date.today(),
    idempotency_key=f"commit:{batch_id}",
)

commit_result = psp.commit_payroll_batch(batch)

# commit_result.status          → CommitStatus enum (APPROVED, BLOCKED_POLICY, BLOCKED_FUNDS, PARTIAL)
# commit_result.batch_id        → UUID of the batch
# commit_result.reservation_id  → UUID of the fund reservation (or None if blocked)
# commit_result.total_amount    → Decimal total committed
# commit_result.approved_count  → number of items approved
# commit_result.blocked_count   → number of items blocked
# commit_result.correlation_id  → UUID for tracing
```

### Executing payments

The execute step runs the **pay gate** (do we still have the money right now?) and submits payment instructions to the configured rail provider.

```python
execute_result = psp.execute_payments(
    tenant_id=tenant_id,
    legal_entity_id=legal_entity_id,
    batch_id=batch_id,
    funding_account_id=funding_account_id,
    items=batch.items,
    reservation_id=commit_result.reservation_id,
    rail="ach",  # optional, defaults to config.default_rail
)

# execute_result.status          → ExecuteStatus enum (SUCCESS, PARTIAL, FAILED, BLOCKED)
# execute_result.submitted_count → number sent to provider
# execute_result.failed_count    → number that failed the pay gate
# execute_result.failures        → list of failure detail dicts
# execute_result.correlation_id  → UUID for tracing
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

# ingest_result.status              → IngestStatus enum (SUCCESS, PARTIAL, FAILED)
# ingest_result.records_processed   → total records handled
# ingest_result.records_matched     → successfully matched to instructions
# ingest_result.records_created     → new settlement records created
# ingest_result.records_failed      → records that failed processing
# ingest_result.unmatched_trace_ids → list of trace IDs with no matching instruction
# ingest_result.correlation_id      → UUID for tracing
```

Unmatched settlements are flagged for manual review. The system never auto-credits an account from an unmatched record.

### Handling provider callbacks

When a provider sends an async status update (webhook), the facade processes it idempotently:

```python
callback_result = psp.handle_provider_callback(
    tenant_id=tenant_id,
    provider_name="ach",
    callback_type="settlement",
    payload=webhook_payload,
)

# callback_result.status → CallbackStatus enum (PROCESSED, DUPLICATE, INVALID, UNKNOWN)
```

### Querying balances

Balance queries use the `LedgerService` directly, not the PSP facade:

```python
from payroll_engine.psp.services.ledger_service import LedgerService

ledger = LedgerService(session)
balance = ledger.get_balance(tenant_id=tenant_id, account_id=account_id)

# balance.total     → all credits minus all debits
# balance.reserved  → funds held by active reservations
# balance.available → total minus reserved (what can be disbursed)
```

### Replaying events

Every state change in the system emits a domain event. Replay uses the `EventStore` directly:

```python
from payroll_engine.psp.events.store import EventStore

store = EventStore(session)
for event in store.replay(
    tenant_id=tenant_id,
    after=datetime(2025, 1, 1),
    event_types=["PaymentSettled", "PaymentReturned"],
    limit=500,
):
    print(f"{event.timestamp} {event.event_type}: {event.payload}")
```

## Idempotency

Every operation uses idempotency keys to prevent duplicate processing. The `PayrollBatch.idempotency_key` ensures safe retries at the commit level, and the `LedgerService` and `EventStore` enforce idempotency at the database level via unique constraints on `(tenant_id, idempotency_key)`.

```python
# Safe retry pattern — same batch, same idempotency_key
result1 = psp.commit_payroll_batch(batch)
result2 = psp.commit_payroll_batch(batch)
# result1.batch_id == result2.batch_id — no duplicate reservation created
```

At the service level, the `PostResult.is_new` flag indicates whether a ledger entry was newly created or already existed. Downstream actions (emitting events, notifications) should only fire when `is_new` is `True`.

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
