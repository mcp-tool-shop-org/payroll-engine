# Payroll Engine: Executive Summary

## What It Is

An open-source library for building payment systems that move money in regulated contexts (payroll, benefits, treasury).

## The Problem

Most payment systems treat money movement as an afterthought:
- Payments fail silently
- Reconciliation requires manual intervention
- Audit trails are incomplete
- Liability is unclear when things go wrong

## The Solution

Payroll Engine provides infrastructure-grade primitives:

| Component | What It Does |
|-----------|--------------|
| **Ledger** | Append-only, double-entry bookkeeping with database-enforced constraints |
| **Funding Gates** | Two-stage approval: "safe to commit" and "safe to pay" |
| **Event Store** | Every state change captured for audit and replay |
| **Liability Classification** | Clear attribution when payments return |
| **AI Advisory** | Optional insights (disabled by default, cannot move money) |

## Key Differentiators

1. **Library, not service**: You deploy it, you control it
2. **Correctness over convenience**: Database constraints prevent impossible states
3. **Audit-first**: Every operation is traceable
4. **AI boundaries enforced**: Advisory only, non-authoritative

## Who It's For

- Payroll platforms
- Benefits administrators
- Gig economy payment systems
- Treasury management
- Any fintech moving regulated money

## Who It's Not For

- Consumer payment apps (no Stripe-style API)
- Complete payroll solutions (no tax calculation)
- Hosted/managed service seekers

## Technical Requirements

- Python 3.11+
- PostgreSQL 15+
- Your deployment infrastructure

## Trust Documents

| Document | Purpose |
|----------|---------|
| [System Invariants](../psp_invariants.md) | Database-enforced guarantees |
| [Threat Model](../threat_model.md) | Security assumptions |
| [Public API](../public_api.md) | Stability contract |
| [Adoption Kit](../adoption_kit.md) | Evaluation guide |

## License

MIT - use it commercially, modify it, no restrictions.

## Links

- **Repository**: https://github.com/mcp-tool-shop/payroll-engine
- **Documentation**: https://github.com/mcp-tool-shop/payroll-engine/tree/master/docs
- **Issues**: https://github.com/mcp-tool-shop/payroll-engine/issues
