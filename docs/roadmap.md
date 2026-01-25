# Roadmap

This document outlines planned work and explicit non-goals.

## Planned (Next)

### CLI Hooks for AI Modules
- Allow operators to plug AI advisory events into external systems
- Event-driven integration (not polling)
- Structured output for log aggregation

### Event Versioning for AI Report Events
- Schema versioning for `AIAdvisoryEmitted` events
- Backwards-compatible field additions
- Migration path documented

### Additional Payment Providers
- Production-ready ACH provider implementation
- FedNow provider implementation
- Wire transfer provider

### Improved Observability
- Structured logging throughout
- Metrics export (Prometheus-compatible)
- Trace context propagation

## Under Consideration

These may happen if there's demand:

- **AsyncIO support**: Async database operations
- **Multi-currency**: Ledger support for non-USD
- **Batch optimization**: Large batch performance improvements
- **Provider certification**: Test harnesses for provider implementations

## Explicit Non-Goals

These will **not** be built. See [non_goals.md](non_goals.md) for details.

| Feature | Why Not |
|---------|---------|
| Autonomous money movement | AI is advisory-only, always |
| Fraud scoring | Beyond scope; use hooks for external systems |
| Tax calculation | Payroll-specific; too many jurisdictions |
| Employee management | HR system concern, not PSP |
| UI/Dashboard | Library, not application |
| Hosted service | Self-hosted only |
| Crypto custody | Provider abstraction only; no key management |

## Version Policy

| Version | Scope |
|---------|-------|
| Patch (0.1.x) | Bug fixes, docs |
| Minor (0.x.0) | New features, additive API changes |
| Major (x.0.0) | Breaking changes (requires migration) |

We aim to avoid major version bumps. Breaking changes require RFC and migration guide.

## Contributing to the Roadmap

- Open a [Feature Request](https://github.com/mcp-tool-shop/payroll-engine/issues/new?template=feature_request.yml)
- Discuss in [GitHub Discussions](https://github.com/mcp-tool-shop/payroll-engine/discussions)
- Major features require RFC (see [docs/rfcs/](rfcs/))
