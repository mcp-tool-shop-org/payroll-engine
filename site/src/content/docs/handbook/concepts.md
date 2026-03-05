---
title: Concepts
description: Core design principles — why append-only ledgers, dual funding gates, settlement tracking, reversals, and mandatory idempotency.
sidebar:
  order: 3
---

Payroll Engine is shaped by the realities of moving money. Every principle below exists because its absence causes real incidents — silent payment failures, reconciliation gaps, double disbursements, and audit trails that explain nothing.

## Why append-only ledgers

You cannot undo a wire transfer. You cannot un-send an ACH payment. The real world is append-only, so your ledger must be too.

In a traditional system, corrections mutate existing records — an `UPDATE` changes the amount, and the previous value is lost. In Payroll Engine, corrections are new entries. The original entry stays forever. A reversal entry offsets it. Auditors can see what happened, when it was corrected, and why. The database enforces this with triggers that reject `UPDATE` and `DELETE` on ledger entries.

### What this means in practice

- Every modification creates a new row in the ledger
- Balances are computed as the sum of all credits minus all debits for an account
- You can reconstruct any account balance at any point in time by replaying entries
- The system never loses information, even when correcting mistakes

## Why two funding gates

The time between "we approved this payroll batch" and "we are about to send payments" can be hours or days. During that window, other batches may run, deposits may bounce, or manual adjustments may change the available balance.

Payroll Engine enforces two separate checkpoints:

### Commit gate

**Question: "Do we have the money to promise these payments?"**

The commit gate runs when a payroll batch is submitted. It checks available funds and creates reservations — holds on the balance that prevent other batches from spending the same money.

The commit gate is **policy-driven**. In some business contexts, it may allow a batch to proceed with a shortfall (soft fail) if the organization has a funding agreement. The strictness is configurable per tenant.

### Pay gate

**Question: "Do we still have the money right before we send?"**

The pay gate runs immediately before payment submission. It verifies that reserved funds are still available and that no intervening changes have invalidated the commitment. The pay gate is **absolute** — it always hard-fails on insufficient funds. There is no override.

:::caution
The pay gate cannot be disabled in production. Setting `pay_gate_enabled=False` in `FundingGateConfig` is only valid for test environments. The facade enforces this.
:::

### Why not just one gate?

A single gate at commit time creates a dangerous window — between commit and pay, another batch might consume the same funds, a deposit might be reversed, or a manual adjustment might reduce the balance.

A single gate at pay time removes the early warning. You would only discover funding problems at the last moment, leaving no time for the employer to arrange additional funding.

Two gates give you both: early commitment with final verification.

## Why settlement is not payment

"Payment sent" is not "money moved." The relationship between submitting a payment and actually settling it depends on the rail:

| Rail | Typical settlement time |
|------|------------------------|
| ACH | 1-3 business days |
| FedNow | Seconds (but can still fail) |
| Wire | Same day (but expensive) |
| Check | Days to weeks |

Payroll Engine tracks the full payment lifecycle through explicit status transitions:

```
Created -> Queued -> Submitted -> Accepted -> Settled
                        |              |
                        v              v
                      Failed        Reversed
                        |
                        v
                     Canceled
```

**Status only moves forward.** A settled payment cannot go back to submitted. A failed payment cannot be retried by changing its status — you create a new instruction. Database triggers enforce this: backward transitions are rejected at the constraint level.

### Settlement as source of truth

The settlement feed from your bank or processor is the only source of truth for what actually happened. Internal records reflect intent. The settlement feed reflects reality. When there is a conflict, the bank wins.

## Why reversals instead of deletes

When a payment settles and then gets returned by the bank (R01 insufficient funds, R02 account closed, etc.), the original ledger entry cannot be deleted. Instead, Payroll Engine creates a **reversal entry** that offsets the original.

This preserves three critical pieces of information:

1. **The original transaction happened** — it was real, not imagined
2. **When the correction occurred** — the reversal has its own timestamp
3. **Why it was reversed** — the return code and reason are recorded

The balance math works naturally: the original credit plus the reversal debit nets to zero. But both entries remain in the ledger permanently, forming a complete audit trail.

### Liability classification

When a return happens, someone bears the cost. The liability service classifies each return:

- **Employer liability** — the employer provided bad account details
- **PSP liability** — the system failed to catch a known problem
- **Provider liability** — the bank or processor made an error

This classification is also recorded as a domain event, creating a verifiable chain from the original payment through the return to the responsible party.

## Why idempotency is mandatory

Network failures happen. Webhooks replay. Users double-click. Without idempotency, any of these can cause double payments — the most damaging failure mode in a payment system.

Every operation in Payroll Engine has an idempotency key. The database enforces uniqueness on `(tenant_id, idempotency_key)` for every table that accepts writes. The application returns the existing result on conflict rather than creating a duplicate.

### The is_new pattern

Every idempotent write returns an `is_new` flag. Downstream actions (emitting events, notifying external systems, updating caches) only happen when `is_new` is `True`. This prevents cascading duplication — a duplicate payment instruction does not trigger a duplicate submission, does not emit a duplicate event, and does not send a duplicate notification.

### Good vs. bad idempotency keys

Good keys encode the logical operation and are deterministic:

- `commit:{batch_id}` — one commit per batch
- `payment:{batch_id}:{employee_id}` — one payment per employee per batch
- `settlement:{provider}:{trace_id}` — one settlement per bank trace

Bad keys are either too broad (causing collisions across different operations) or too random (defeating idempotency entirely with a new UUID each call).

## Next steps

For the full API contract, stability guarantees, and AI advisory details, see [Reference](/payroll-engine/handbook/reference/).
