---
title: Beginners Guide
description: New to payment systems? This page covers the fundamentals you need before working with Payroll Engine.
sidebar:
  order: 99
---

If you are new to payment processing, payroll systems, or financial engineering, this page covers the foundational knowledge you need before diving into the rest of the handbook.

## What problem does Payroll Engine solve?

When a company pays its employees, the money moves through a chain of systems: the employer's bank, a payment network (like ACH), and the employee's bank. This process is not instant, not guaranteed, and not reversible. Payroll Engine is a library that manages this complexity with correct bookkeeping, so you do not lose track of money.

Most payment systems treat the "send payment" step as a single API call and hope for the best. Payroll Engine breaks it into explicit stages: **commit** (reserve the funds), **execute** (submit to the bank), **settle** (confirm the bank actually moved the money), and **return** (handle failures after settlement). Each stage has its own guarantees and audit trail.

## Key terminology

Understanding these terms will help you read the rest of the handbook without confusion.

| Term | What it means |
|------|---------------|
| **Ledger** | A permanent record of all financial transactions. Like a bank statement, but for your application. Entries are append-only: you never edit or delete a row. |
| **Tenant** | An organization using the system. Every query is scoped to a tenant, so one tenant cannot see another's data. |
| **PSP** | Payment Service Provider. The software layer that manages the flow between your application and the actual banking networks. Payroll Engine is a PSP core. |
| **Funding gate** | A checkpoint that verifies sufficient funds exist before allowing a payment to proceed. Payroll Engine has two: commit gate and pay gate. |
| **Settlement** | The confirmation from the bank that money actually moved. "Payment submitted" is not the same as "payment settled." |
| **Idempotency** | The property that repeating an operation produces the same result. If your network call fails and you retry, you do not get double payments. |
| **Reversal** | When a settled payment fails (e.g., the recipient's account was closed), the bank returns it. A reversal entry offsets the original in the ledger. |
| **Domain event** | A record of something that happened in the system (e.g., "PaymentSettled", "FundingBlocked"). Events are immutable and replayable. |

## How money actually moves

Understanding the real-world flow helps you understand why Payroll Engine works the way it does.

### The ACH example

ACH (Automated Clearing House) is the most common way to pay employees in the US. Here is a simplified timeline:

1. **Day 1 (Monday)**: Your application sends a batch of payment instructions to the ACH network through a bank.
2. **Day 1-2**: The ACH network routes each payment to the recipient's bank.
3. **Day 2-3**: The recipient's bank accepts or rejects the payment.
4. **Day 3+**: You receive a settlement file confirming which payments succeeded and which were returned.

During this entire window, you do not know for certain whether the money arrived. Payroll Engine tracks each payment through these stages so your application always knows the current state.

### Why "payment sent" is not enough

A common mistake in payment systems is treating the submission as the final step. In reality, payments can fail days after submission for reasons like:

- **R01**: Insufficient funds in the recipient's account
- **R02**: Account closed
- **R03**: No account found (bad routing number)
- **R04**: Invalid account number

Payroll Engine's settlement ingestion and return handling exist specifically for this gap between submission and confirmation.

## The two-gate funding model

Before you send money, you need to verify it exists. Payroll Engine does this twice:

1. **Commit gate** (early check): When a payroll batch is submitted, the commit gate verifies that the funding account has enough money and creates a **reservation** (a hold on those funds). This prevents two batches from spending the same money.

2. **Pay gate** (final check): Immediately before actually sending payments, the pay gate re-verifies the funds. This catches any changes that occurred between commit and pay -- other batches running, deposits bouncing, or manual adjustments.

The pay gate is absolute. It cannot be disabled in production. The commit gate is configurable (strict or soft-fail) depending on business needs.

## Why the ledger is append-only

In a traditional database, you might fix a mistake by updating a row. In financial systems, this destroys the audit trail. If a regulator asks "what was the balance at 2 PM on Tuesday?", you cannot answer that question if you have been overwriting records.

Payroll Engine's ledger never updates or deletes entries. To correct a mistake, you add a new entry that offsets the original. This means:

- You can always reconstruct any balance at any point in time
- Every change has a timestamp and a reason
- Auditors can trace the full history of any account

The database itself enforces this with triggers that reject `UPDATE` and `DELETE` operations on ledger tables. Even if you write raw SQL, you cannot break this guarantee.

## Your first integration (mental model)

Here is the simplest conceptual flow for integrating Payroll Engine into your application:

```
1. Create a PSP instance (wires up the ledger, gates, and providers)
2. Build a PayrollBatch (list of employees and amounts)
3. Call commit_payroll_batch() → funds are reserved
4. Call execute_payments() → payments are submitted to the bank
5. Later, call ingest_settlement_feed() → confirm what the bank actually did
6. Handle any returns → reversals and liability classification
```

Each step produces domain events that you can subscribe to for notifications, metrics, or downstream processing. The facade (the `PSP` class) enforces the correct order and prevents you from skipping steps.

For concrete code examples, proceed to [Getting Started](/payroll-engine/handbook/getting-started/) to set up a local environment, then [Usage](/payroll-engine/handbook/usage/) for the actual API calls.

## Common mistakes to avoid

These are patterns that cause real incidents in payment systems. Payroll Engine prevents most of them by design, but understanding them helps you use the library correctly.

| Mistake | Why it is dangerous | How Payroll Engine prevents it |
|---------|--------------------|---------------------------------|
| Treating submission as settlement | You mark payments "done" before the bank confirms | Status tracking requires explicit settlement ingestion |
| Deleting or updating ledger records | Audit trail is destroyed | Database triggers reject mutations |
| Skipping the pay gate | Funds may have changed since commit | Pay gate is always enforced (no bypass in production) |
| Using random UUIDs as idempotency keys | Retries create duplicates instead of being safe | Documentation and patterns enforce stable, deterministic keys |
| Ignoring unmatched settlements | Money moved that you are not tracking | Unmatched records are flagged, never auto-credited |
| Single funding check | Window between check and payment allows double-spending | Two gates: commit (early) and pay (final) |
