-- Migration 204: Liability Events
-- Creates the liability_event table for tracking payment failures,
-- returns, and their recovery lifecycle.

CREATE TABLE IF NOT EXISTS liability_event (
    liability_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant isolation
    tenant_id UUID NOT NULL,
    legal_entity_id UUID NOT NULL,

    -- Source reference (payment_instruction, settlement_event, etc.)
    source_type TEXT NOT NULL,
    source_id UUID NOT NULL,

    -- Classification
    error_origin TEXT NOT NULL,      -- client, payroll_engine, provider, bank, recipient
    liability_party TEXT NOT NULL,   -- client, psp, provider, recipient
    loss_amount NUMERIC NOT NULL,

    -- Recovery tracking
    recovery_path TEXT,              -- offset, clawback, dispute, insurance_claim, write_off
    recovery_status TEXT NOT NULL DEFAULT 'pending',
    recovery_amount NUMERIC DEFAULT 0,

    -- Determination
    determined_by_user_id UUID,
    determination_reason TEXT,
    evidence_json JSONB,

    -- Deduplication
    idempotency_key TEXT,

    -- Lifecycle
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_liability_event_tenant
    ON liability_event (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_liability_event_source
    ON liability_event (source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_liability_event_status
    ON liability_event (tenant_id, recovery_status);

-- Idempotency: unique per tenant when key is present
CREATE UNIQUE INDEX IF NOT EXISTS idx_liability_event_idempotency
    ON liability_event (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

COMMENT ON TABLE liability_event IS
    'Tracks payment failures, returns, and their recovery lifecycle.';
