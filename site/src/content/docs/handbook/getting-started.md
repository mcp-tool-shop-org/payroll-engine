---
title: Getting Started
description: Prerequisites, installation options, and running the PSP demo end-to-end.
sidebar:
  order: 1
---

This page covers everything you need to install Payroll Engine, spin up a local database, and run the full payment lifecycle demo.

## Prerequisites

- **Python 3.11+** — the library uses modern type annotations and dataclass features
- **PostgreSQL 14+** — the ledger relies on database-level constraints, triggers, and append-only enforcement
- **Docker & Docker Compose** — for the quickest local setup (the Makefile wraps Docker commands)

## Installation

Payroll Engine is published on PyPI. Install only the extras you need — the core has no optional dependencies.

```bash
# Core only (ledger, funding gate, payments — that's it)
pip install payroll-engine

# With PostgreSQL driver (psycopg2)
pip install payroll-engine[postgres]

# With async PostgreSQL support (asyncpg)
pip install payroll-engine[asyncpg]

# With AI advisory features (optional, disabled by default)
pip install payroll-engine[ai]

# Development dependencies (pytest, ruff, pyright)
pip install payroll-engine[dev]

# Everything
pip install payroll-engine[all]
```

:::note
The core money-movement functionality requires **zero optional dependencies**. The `[ai]`, `[postgres]`, and `[asyncpg]` extras add capabilities but are never required for the ledger or funding gates to work.
:::

### From source (recommended for evaluation)

```bash
git clone https://github.com/mcp-tool-shop-org/payroll-engine.git
cd payroll-engine
pip install -e ".[dev]"
```

### Full local stack (recommended for running the demo)

```bash
pip install -e ".[all]"
```

## Quick start with Make

The Makefile is the fastest path to a running system.

```bash
# Start PostgreSQL in Docker
make up

# Apply database migrations (forward-only, deterministic)
make migrate

# Run the full lifecycle demo
make demo
```

### What the demo does

The demo (`examples/psp_minimal/main.py`) walks through the entire payment lifecycle in order:

1. **Create tenant and accounts** — sets up the organizational hierarchy and funding accounts
2. **Fund the account** — posts an initial funding ledger entry
3. **Commit a payroll batch** — runs the commit gate and creates fund reservations
4. **Execute payments** — runs the pay gate (verifies funds again) and submits to the payment rail
5. **Simulate a settlement feed** — ingests external bank confirmations
6. **Handle a return with liability classification** — processes a failed settlement, creates reversal entries, and classifies who bears the loss
7. **Replay events** — replays the full domain event history for deterministic debugging

### Other Make targets

```bash
make reset       # Full reset: stop, delete data, restart, migrate
make health      # Check database health and row counts
make test        # Run all tests
make test-psp    # Run PSP-specific tests only
make lint        # Run ruff linter
make typecheck   # Run pyright type checker
make ci          # Run all CI checks (lint + typecheck + test)
```

## Verifying the database

After migrations, verify that the database constraints are properly in place:

```bash
psp schema-check --database-url "$DATABASE_URL"
```

This checks that all critical constraints exist — append-only triggers, positive amount checks, unique idempotency keys, and forward-only status transitions. If any constraint is missing, the command will report exactly what is wrong.

## Next steps

Once the demo runs successfully, move on to [Usage](/payroll-engine/handbook/usage/) to learn how to embed the PSP facade in your own application.
