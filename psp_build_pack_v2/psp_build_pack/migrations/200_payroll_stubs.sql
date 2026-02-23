-- Migration 200: Payroll Schema Stubs for PSP
-- Creates minimal versions of main payroll tables needed by PSP services.
-- Uses IF NOT EXISTS for compatibility when full main schema is present.
-- Adds PSP-specific columns that the funding gate service requires.

-- =============================================================================
-- Core domain tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS tenant (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legal_entity (
    legal_entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    legal_name TEXT NOT NULL,
    fein TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS employee (
    employee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    ssn_last4 TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS employment (
    employment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL,
    legal_entity_id UUID NOT NULL,
    hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
    employment_type TEXT NOT NULL DEFAULT 'full_time',
    flsa_status TEXT NOT NULL DEFAULT 'non_exempt',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pay_schedule (
    pay_schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    legal_entity_id UUID NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    frequency TEXT NOT NULL DEFAULT 'biweekly',
    anchor_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Pay run tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS pay_run (
    pay_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    legal_entity_id UUID,
    pay_schedule_id UUID,
    status TEXT NOT NULL DEFAULT 'draft',
    period_start DATE,
    period_end DATE,
    check_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pay_run_employee (
    pay_run_employee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pay_run_id UUID NOT NULL,
    employment_id UUID,
    employee_id UUID,
    status TEXT NOT NULL DEFAULT 'included',
    calculation_version TEXT NOT NULL DEFAULT '1.0.0',
    gross NUMERIC(14,4) NOT NULL DEFAULT 0,
    net NUMERIC(14,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pay_statement (
    pay_statement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pay_run_employee_id UUID NOT NULL,
    check_date DATE NOT NULL DEFAULT CURRENT_DATE,
    payment_method TEXT NOT NULL DEFAULT 'ach',
    statement_status TEXT NOT NULL DEFAULT 'issued',
    gross_pay NUMERIC(14,4) NOT NULL DEFAULT 0,
    net_pay NUMERIC(14,4) NOT NULL DEFAULT 0,
    total_deductions NUMERIC(14,4) NOT NULL DEFAULT 0,
    total_taxes NUMERIC(14,4) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'final',
    calculation_id UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pay_line_item (
    pay_line_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pay_statement_id UUID NOT NULL,
    line_type TEXT NOT NULL DEFAULT 'EARNING',
    category TEXT,
    amount NUMERIC(14,4) NOT NULL DEFAULT 0,
    is_third_party_remit BOOLEAN DEFAULT false,
    calculation_id UUID NOT NULL DEFAULT gen_random_uuid(),
    line_hash TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- If main schema already created these tables without PSP-specific columns,
-- add the columns the PSP funding gate service needs.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_run' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE pay_run ADD COLUMN tenant_id UUID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_run' AND column_name = 'check_date'
    ) THEN
        ALTER TABLE pay_run ADD COLUMN check_date DATE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_line_item' AND column_name = 'category'
    ) THEN
        ALTER TABLE pay_line_item ADD COLUMN category TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_line_item' AND column_name = 'is_third_party_remit'
    ) THEN
        ALTER TABLE pay_line_item ADD COLUMN is_third_party_remit BOOLEAN DEFAULT false;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_run' AND column_name = 'pay_schedule_id'
    ) THEN
        ALTER TABLE pay_run ADD COLUMN pay_schedule_id UUID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_run' AND column_name = 'period_start'
    ) THEN
        ALTER TABLE pay_run ADD COLUMN period_start DATE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_run' AND column_name = 'period_end'
    ) THEN
        ALTER TABLE pay_run ADD COLUMN period_end DATE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_run_employee' AND column_name = 'employment_id'
    ) THEN
        ALTER TABLE pay_run_employee ADD COLUMN employment_id UUID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_statement' AND column_name = 'gross_pay'
    ) THEN
        ALTER TABLE pay_statement ADD COLUMN gross_pay NUMERIC(14,4) NOT NULL DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_statement' AND column_name = 'total_deductions'
    ) THEN
        ALTER TABLE pay_statement ADD COLUMN total_deductions NUMERIC(14,4) NOT NULL DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_statement' AND column_name = 'total_taxes'
    ) THEN
        ALTER TABLE pay_statement ADD COLUMN total_taxes NUMERIC(14,4) NOT NULL DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_statement' AND column_name = 'status'
    ) THEN
        ALTER TABLE pay_statement ADD COLUMN status TEXT NOT NULL DEFAULT 'final';
    END IF;
END $$;

-- Indexes for PSP queries
CREATE INDEX IF NOT EXISTS idx_pay_run_tenant ON pay_run(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pay_run_legal_entity ON pay_run(legal_entity_id);
CREATE INDEX IF NOT EXISTS idx_pre_pay_run ON pay_run_employee(pay_run_id);
CREATE INDEX IF NOT EXISTS idx_ps_pre ON pay_statement(pay_run_employee_id);
CREATE INDEX IF NOT EXISTS idx_pli_ps ON pay_line_item(pay_statement_id);

COMMENT ON TABLE pay_run IS
    'Payroll run stub for PSP standalone operation. Full schema in migrations/001.';
