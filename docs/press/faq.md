# Frequently Asked Questions

## General

### What is Payroll Engine?

A library for building payment systems that move money in regulated contexts. It provides ledger, funding gates, event sourcing, and optional AI advisory capabilities.

### Is this a service I can sign up for?

No. This is a library you embed in your application. You deploy it, manage the database, and control operational policy.

### What's the license?

MIT. Use it commercially, modify it, no restrictions.

### Who built this?

Engineers with experience in payroll and payment infrastructure who've dealt with payment failures, reconciliation nightmares, and 3 AM pages.

---

## AI Advisory

### Can the AI move money?

**No.** This is enforced at the architecture level:
- AI modules have no write access to ledger
- AI cannot bypass funding gates
- AI emits advisory events only
- Human/policy review required for all actions

### Is AI enabled by default?

**No.** `AdvisoryConfig.enabled` defaults to `False`. You must explicitly opt in.

### What does the AI actually do?

Advisory analysis:
- Return prediction and analysis
- Funding risk assessment
- Operational insights
- Runbook assistance (suggests queries, never executes them)

### Can I use it without AI?

Yes. AI is completely optional. The core PSP (ledger, gates, payments) works without any AI features.

### Does the AI require external APIs?

No. The `rules_baseline` model is purely deterministic and runs locally with no dependencies beyond Python stdlib. Future ML models may require additional dependencies.

---

## Crypto Rails

### Does this support cryptocurrency payments?

The architecture supports crypto payment providers, but:
- No providers ship in v0.1.0
- Crypto is an optional extra (`[crypto]`)
- No custody or key management included
- You implement the provider protocol

### Will you add crypto custody?

**No.** See [non_goals.md](../non_goals.md). Custody is out of scope. We provide the payment abstraction; custody is your responsibility.

---

## Compliance

### Is this compliant with [regulation X]?

We provide infrastructure that supports compliance (audit trails, immutable records, liability tracking). Compliance itself is your responsibility based on your jurisdiction and use case.

### Does this handle PCI compliance?

This library doesn't process card data. If you integrate with card networks, PCI compliance is your responsibility.

### What about SOC 2?

The audit capabilities (immutable events, replay, provenance) support SOC 2 controls. Certification is your responsibility.

---

## Technical

### What database does it require?

PostgreSQL 15+. The constraints and triggers rely on PostgreSQL-specific features.

### Can I use MySQL/SQLite/MongoDB?

Not currently. The invariants are enforced via PostgreSQL constraints. Porting would require reimplementing these guarantees.

### Is there async support?

Not in v0.1.0. The API is synchronous. AsyncIO support is under consideration.

### How do I add a new payment provider?

Implement the `PaymentRailProvider` protocol. See [recipes/custom_provider.md](../recipes/custom_provider.md).

---

## Operations

### What happens when payments fail?

1. Payment status transitions to failed state
2. Domain event emitted
3. Runbook documents investigation steps
4. AI advisory (if enabled) provides analysis

### How do I handle returns?

1. Ingest settlement feed with return data
2. System classifies liability (employer, employee, provider, platform)
3. Reversal entries created in ledger
4. Events emitted for downstream processing

### Can I replay events?

Yes. Events are immutable and replayable. Use `psp replay-events` CLI command or programmatic API.

---

## Adoption

### How do I evaluate this for my use case?

Start with [docs/adoption_kit.md](../adoption_kit.md). It covers:
- Evaluation checklist
- Integration patterns
- Red flags to watch for

### What's the learning curve?

If you understand double-entry bookkeeping and event sourcing, the concepts are familiar. The main learning is understanding the specific invariants and funding gate semantics.

### Is there commercial support?

Not currently offered. Community support via GitHub Discussions.

---

## Contributing

### How do I contribute?

See [CONTRIBUTING.md](../../CONTRIBUTING.md). Key rules:
- All changes need tests
- Money-affecting changes need extra scrutiny
- Event schema changes must be backwards-compatible

### Can I add feature X?

Check [non_goals.md](../non_goals.md) first. If it's not a non-goal, open an issue to discuss before implementing.
