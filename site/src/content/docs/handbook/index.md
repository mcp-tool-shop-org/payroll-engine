---
title: Payroll Engine Handbook
description: A comprehensive guide to the library-first PSP core for payroll and regulated money movement.
sidebar:
  order: 0
---

Welcome to the Payroll Engine Handbook. This is your companion for understanding, integrating, and operating the PSP (Payment Service Provider) core library.

## What is Payroll Engine?

Payroll Engine is a **library-first PSP core** for payroll and regulated money movement. It provides a deterministic, append-only ledger with explicit funding gates, replayable domain events, and advisory-only AI. The design philosophy is **correctness over convenience** — every guarantee is enforced at the database and code level, not just documented.

## Who is this for?

Payroll Engine is built for teams that move money in regulated contexts:

- **Payroll engines** processing employee compensation
- **Gig economy platforms** disbursing contractor payments
- **Benefits administrators** managing healthcare and retirement fund flows
- **Treasury management** systems tracking corporate cash movement
- **Any regulated fintech backend** where audit trails and correctness are non-negotiable

## Handbook sections

| Section | What you will learn |
|---------|---------------------|
| [Getting Started](/payroll-engine/handbook/getting-started/) | Prerequisites, installation, and running the demo |
| [Usage](/payroll-engine/handbook/usage/) | Library integration, CLI tools, and testing |
| [Concepts](/payroll-engine/handbook/concepts/) | Core principles — why the system works this way |
| [Reference](/payroll-engine/handbook/reference/) | API stability, guarantees, AI advisory, and security |
| [Beginners](/payroll-engine/handbook/beginners/) | New to payment systems? Start here for the fundamentals |

## Trust anchors

Before adopting Payroll Engine in production, review these documents in the repository:

- **[psp_invariants.md](https://github.com/mcp-tool-shop-org/payroll-engine/blob/main/docs/psp_invariants.md)** — System invariants (what is guaranteed, and how)
- **[threat_model.md](https://github.com/mcp-tool-shop-org/payroll-engine/blob/main/docs/threat_model.md)** — Security analysis (STRIDE methodology, attack scenarios, mitigations)
- **[public_api.md](https://github.com/mcp-tool-shop-org/payroll-engine/blob/main/docs/public_api.md)** — Public API contract (what is stable, what is internal)
- **[adoption_kit.md](https://github.com/mcp-tool-shop-org/payroll-engine/blob/main/docs/adoption_kit.md)** — Evaluation and embedding guide

We know this moves money. These documents prove we took it seriously.
