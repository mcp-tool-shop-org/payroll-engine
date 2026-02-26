import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'Payroll Engine',
  description: 'Library-first PSP core for payroll and regulated money movement. Append-only ledger, funding gates, domain events, advisory-only AI.',
  logoBadge: 'PE',
  brandName: 'Payroll Engine',
  repoUrl: 'https://github.com/mcp-tool-shop-org/payroll-engine',
  footerText: 'MIT Licensed — built by <a href="https://github.com/mcp-tool-shop-org" style="color:var(--color-muted);text-decoration:underline">mcp-tool-shop-org</a>',

  hero: {
    badge: 'Open source',
    headline: 'Payroll Engine',
    headlineAccent: 'Correctness over convenience.',
    description: 'A library-first PSP core for payroll and regulated money movement. Append-only ledger, explicit funding gates, replayable events, and advisory-only AI.',
    primaryCta: { href: '#quick-start', label: 'Get started' },
    secondaryCta: { href: '#features', label: 'Learn more' },
    previews: [
      { label: 'Install', code: 'pip install payroll-engine' },
      { label: 'Init', code: 'psp = PSP(session=session, config=config)' },
      { label: 'Commit', code: 'psp.commit_payroll_batch(batch)' },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'Core Features',
      subtitle: 'Production-grade money movement with no shortcuts.',
      features: [
        { title: 'Append-Only Ledger', desc: 'Every modification is a new entry. No UPDATEs, no DELETEs. History is always preserved and auditable.' },
        { title: 'Dual Funding Gates', desc: 'Commit gate reserves funds. Pay gate verifies again before sending. The pay gate cannot be bypassed.' },
        { title: 'Replayable Events', desc: 'Domain events are immutable and versioned. Replay any sequence for debugging, audit, or reconciliation.' },
        { title: 'Settlement Tracking', desc: 'Full payment lifecycle from Created to Settled. ACH, FedNow, wire — each rail tracked separately.' },
        { title: 'Advisory-Only AI', desc: 'AI can score risk, analyze returns, and suggest runbooks. It can never move money or write ledger entries.' },
        { title: 'Idempotent Operations', desc: 'Every operation has an idempotency key. Retry safely without double payments or duplicate entries.' },
      ],
    },
    {
      kind: 'code-cards',
      id: 'quick-start',
      title: 'Quick Start',
      cards: [
        {
          title: 'Install',
          code: '# Core only\npip install payroll-engine\n\n# With PostgreSQL\npip install payroll-engine[postgres]\n\n# With AI advisory\npip install payroll-engine[ai]',
        },
        {
          title: 'Library usage',
          code: 'from payroll_engine.psp import PSP, PSPConfig\n\nconfig = PSPConfig(\n    tenant_id=tenant_id,\n    ledger=LedgerConfig(require_balanced_entries=True),\n    funding_gate=FundingGateConfig(pay_gate_enabled=True),\n)\n\npsp = PSP(session=session, config=config)\nresult = psp.commit_payroll_batch(batch)',
        },
      ],
    },
    {
      kind: 'features',
      id: 'principles',
      title: 'Design Principles',
      subtitle: 'Built by engineers who\'ve been paged at 3 AM because payments failed silently.',
      features: [
        { title: 'Reversals, Not Deletes', desc: 'When money moves wrong, a reversal entry offsets the original. Both entries stay in the ledger forever.' },
        { title: 'Settlement ≠ Payment', desc: '"Payment sent" is not "money moved." Track the full lifecycle: Created → Submitted → Accepted → Settled.' },
        { title: 'Library, Not Service', desc: 'Embed PSP inside your application. No separate service to deploy, monitor, or fail independently.' },
      ],
    },
    {
      kind: 'data-table',
      id: 'guarantees',
      title: 'Key Guarantees',
      columns: ['Guarantee', 'Enforcement'],
      rows: [
        ['Money is always positive', 'CHECK (amount > 0)'],
        ['No self-transfers', 'CHECK (debit != credit)'],
        ['Ledger is append-only', 'No UPDATE/DELETE on entries'],
        ['Status only moves forward', 'Trigger validates transitions'],
        ['Events are immutable', 'Schema versioning in CI'],
        ['Pay gate cannot be bypassed', 'Enforced in facade'],
        ['AI cannot move money', 'Architectural constraint'],
      ],
    },
    {
      kind: 'data-table',
      id: 'extras',
      title: 'Optional Extras',
      columns: ['Extra', 'What It Adds', 'Default State'],
      rows: [
        ['[postgres]', 'PostgreSQL driver', 'Not loaded unless used'],
        ['[asyncpg]', 'Async PostgreSQL', 'Not loaded unless used'],
        ['[ai]', 'ML-based AI models', 'Not needed for rules-baseline'],
        ['[crypto]', 'Blockchain integrations (future)', 'OFF — reserved'],
      ],
    },
    {
      kind: 'code-cards',
      id: 'cli',
      title: 'CLI Tools',
      cards: [
        {
          title: 'Health & schema',
          code: '# Check database health\npsp health\n\n# Verify schema constraints\npsp schema-check --database-url $DATABASE_URL',
        },
        {
          title: 'Events & audit',
          code: '# Replay events\npsp replay-events --tenant-id $TENANT --since "2025-01-01"\n\n# Export for audit\npsp export-events --tenant-id $TENANT --output events.jsonl',
        },
      ],
    },
    {
      kind: 'data-table',
      id: 'docs',
      title: 'Documentation',
      columns: ['Document', 'Purpose'],
      rows: [
        ['psp_invariants.md', 'System invariants — what\'s guaranteed'],
        ['threat_model.md', 'Security analysis'],
        ['public_api.md', 'Public API contract — what\'s stable'],
        ['idempotency.md', 'Idempotency patterns'],
        ['adoption_kit.md', 'Evaluation and embedding guide'],
        ['non_goals.md', 'What PSP doesn\'t do'],
      ],
    },
  ],
};
