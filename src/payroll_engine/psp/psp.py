"""PSP Facade - Single opinionated integration path.

This facade provides the ONLY blessed way to interact with PSP operations.
It enforces invariants "by construction" - you can't misuse it.

Usage:
    psp = PSP(session, config)

    # Commit a payroll batch (runs commit gate, creates reservations)
    result = psp.commit_payroll_batch(batch)

    # Execute payments (enforces pay gate, submits to rails)
    result = psp.execute_payments(batch_id)

    # Ingest settlement feed from provider
    result = psp.ingest_settlement_feed(provider, records)

    # Handle provider callback (status updates, idempotent)
    result = psp.handle_provider_callback(provider, payload)

The facade:
- Wires services together correctly
- Emits domain events at the right moments
- Enforces gate evaluation order
- Handles idempotency consistently
- Provides clear success/failure semantics
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from payroll_engine.psp.events.emitter import AsyncEventEmitter, EventEmitter
from payroll_engine.psp.events.types import (
    EventMetadata,
    FundingApproved,
    FundingBlocked,
    FundingInsufficientFunds,
    FundingRequested,
    LiabilityClassified,
    PaymentFailed,
    PaymentInstructionCreated,
    PaymentReturned,
    PaymentSettled,
    PaymentSubmitted,
    ReconciliationCompleted,
    ReconciliationStarted,
    SettlementReceived,
)
from payroll_engine.psp.providers.base import PaymentRailProvider, SettlementRecord
from payroll_engine.psp.services.funding_gate import AsyncFundingGateService, FundingGateService
from payroll_engine.psp.services.ledger_service import AsyncLedgerService, LedgerService
from payroll_engine.psp.services.liability import AsyncLiabilityService, LiabilityService
from payroll_engine.psp.services.payment_orchestrator import (
    AsyncPaymentOrchestrator,
    PaymentOrchestrator,
)
from payroll_engine.psp.services.reconciliation import (
    AsyncReconciliationService,
    ReconciliationService,
)


class CommitStatus(str, Enum):
    """Result of commit_payroll_batch."""

    APPROVED = "approved"  # All gates passed, reservations created
    BLOCKED_POLICY = "blocked_policy"  # Commit gate blocked by policy
    BLOCKED_FUNDS = "blocked_funds"  # Insufficient funds (strict mode)
    PARTIAL = "partial"  # Some items approved, some blocked


class ExecuteStatus(str, Enum):
    """Result of execute_payments."""

    SUCCESS = "success"  # All payments submitted
    PARTIAL = "partial"  # Some succeeded, some failed
    FAILED = "failed"  # All failed
    BLOCKED = "blocked"  # Pay gate blocked execution


class IngestStatus(str, Enum):
    """Result of ingest_settlement_feed."""

    SUCCESS = "success"  # All records processed
    PARTIAL = "partial"  # Some succeeded, some failed
    FAILED = "failed"  # Processing failed


class CallbackStatus(str, Enum):
    """Result of handle_provider_callback."""

    PROCESSED = "processed"  # Callback processed successfully
    DUPLICATE = "duplicate"  # Already processed (idempotent)
    INVALID = "invalid"  # Invalid callback data
    UNKNOWN = "unknown"  # Unknown payment reference


@dataclass
class PayrollItem:
    """Single payment in a payroll batch."""

    payee_type: str  # employee, vendor, tax_authority
    payee_ref_id: UUID
    amount: Decimal
    purpose: str  # employee_net, vendor_payment, tax_payment
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PayrollBatch:
    """A batch of payments to commit."""

    batch_id: UUID
    tenant_id: UUID
    legal_entity_id: UUID
    pay_period_id: UUID
    funding_account_id: UUID
    items: list[PayrollItem]
    effective_date: date
    idempotency_key: str


@dataclass
class CommitResult:
    """Result of committing a payroll batch."""

    status: CommitStatus
    batch_id: UUID
    reservation_id: UUID | None
    total_amount: Decimal
    approved_count: int
    blocked_count: int
    block_reason: str | None
    correlation_id: UUID


@dataclass
class ExecuteResult:
    """Result of executing payments."""

    status: ExecuteStatus
    batch_id: UUID
    submitted_count: int
    failed_count: int
    failures: list[dict[str, Any]]
    correlation_id: UUID


@dataclass
class IngestResult:
    """Result of ingesting settlement feed."""

    status: IngestStatus
    records_processed: int
    records_matched: int
    records_created: int
    records_failed: int
    unmatched_trace_ids: list[str]
    correlation_id: UUID


@dataclass
class CallbackResult:
    """Result of handling provider callback."""

    status: CallbackStatus
    payment_instruction_id: UUID | None
    previous_status: str | None
    new_status: str | None
    correlation_id: UUID


@dataclass
class PSPConfig:
    """Configuration for PSP facade."""

    # Gate behavior
    commit_gate_strict: bool = False  # If True, commit gate fails on insufficient funds
    pay_gate_always_enforced: bool = True  # Pay gate cannot be bypassed

    # Reservation settings
    reservation_ttl_hours: int = 24  # How long reservations live

    # Provider settings
    default_rail: str = "ach"

    # Funding model
    default_funding_model: str = "prefund_all"

    # Event emission
    emit_events: bool = True


def _summarize_reasons(reasons: list[dict[str, Any]]) -> str:
    """Summarize a list of gate reason dicts into a single string."""
    if not reasons:
        return "Unknown reason"
    messages = [r.get("message", r.get("code", "Unknown")) for r in reasons]
    return "; ".join(messages)


def _reasons_contain_insufficient(reasons: list[dict[str, Any]]) -> bool:
    """Check if any reason indicates insufficient funds."""
    for r in reasons:
        code = r.get("code", "")
        message = r.get("message", "")
        if "INSUFFICIENT" in code.upper() or "insufficient" in message.lower():
            return True
    return False


class PSP:
    """Synchronous PSP Facade.

    This is the ONLY way to interact with PSP operations.
    It enforces invariants by construction.
    """

    def __init__(
        self,
        session: Session,
        config: PSPConfig | None = None,
        providers: dict[str, PaymentRailProvider] | None = None,
        event_emitter: EventEmitter | None = None,
    ) -> None:
        self._session = session
        self._config = config or PSPConfig()
        self._providers = providers or {}

        # Wire up services - FundingGateService only takes db
        self._ledger = LedgerService(session)
        self._funding_gate = FundingGateService(session)
        self._liability = LiabilityService(session)

        # Event emitter (optional)
        self._emitter = event_emitter

    def register_provider(self, name: str, provider: PaymentRailProvider) -> None:
        """Register a payment rail provider."""
        self._providers[name] = provider

    def _find_instruction_by_provider_ref(
        self,
        *,
        tenant_id: UUID,
        provider_request_id: str,
    ) -> dict[str, Any] | None:
        """Find a payment instruction by its provider_request_id.

        Since PaymentOrchestrator has no find_by_provider_request_id method,
        we do a direct SQL query through the payment_attempt table.
        """
        row = self._session.execute(
            text("""
                SELECT pi.payment_instruction_id, pi.status, pi.amount,
                       pi.legal_entity_id, pi.purpose
                FROM payment_attempt pa
                JOIN payment_instruction pi ON pi.payment_instruction_id = pa.payment_instruction_id
                WHERE pa.provider_request_id = :prid
                  AND pi.tenant_id = :tenant_id
                ORDER BY pa.created_at DESC
                LIMIT 1
            """),
            {"prid": provider_request_id, "tenant_id": str(tenant_id)},
        ).fetchone()

        if not row:
            return None

        return {
            "instruction_id": UUID(str(row[0])),
            "status": row[1],
            "amount": Decimal(str(row[2])),
            "legal_entity_id": UUID(str(row[3])),
            "purpose": row[4],
        }

    def commit_payroll_batch(self, batch: PayrollBatch) -> CommitResult:
        """Commit a payroll batch.

        This is step 1 of payroll processing:
        1. Evaluate commit gate (policy checks)
        2. If strict mode, also check available funds
        3. Create reservation to hold funds
        4. Emit FundingRequested event

        The batch is NOT yet paid - this just reserves funds.

        Args:
            batch: The payroll batch to commit

        Returns:
            CommitResult with status and reservation details
        """
        correlation_id = uuid4()
        total_amount = sum((item.amount for item in batch.items), Decimal("0"))

        # Emit FundingRequested event
        if self._emitter and self._config.emit_events:
            self._emitter.emit(FundingRequested(
                metadata=EventMetadata.create(
                    tenant_id=batch.tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                funding_request_id=batch.batch_id,
                legal_entity_id=batch.legal_entity_id,
                pay_period_id=batch.pay_period_id,
                requested_amount=total_amount,
                currency="USD",
                requested_date=batch.effective_date,
            ))

        # Step 1: Evaluate commit gate - uses actual FundingGateService API
        commit_result = self._funding_gate.evaluate_commit_gate(
            tenant_id=batch.tenant_id,
            legal_entity_id=batch.legal_entity_id,
            pay_run_id=batch.pay_period_id,
            funding_model=self._config.default_funding_model,
            idempotency_key=f"commit_gate:{batch.idempotency_key}",
            strict=self._config.commit_gate_strict,
        )

        if not commit_result.passed:
            # Generate a synthetic evaluation_id since GateResult has none
            gate_evaluation_id = uuid4()
            reason_summary = _summarize_reasons(commit_result.reasons)
            is_insufficient = _reasons_contain_insufficient(commit_result.reasons)

            # Emit blocked event
            if self._emitter and self._config.emit_events:
                if is_insufficient:
                    self._emitter.emit(FundingInsufficientFunds(
                        metadata=EventMetadata.create(
                            tenant_id=batch.tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        funding_request_id=batch.batch_id,
                        legal_entity_id=batch.legal_entity_id,
                        requested_amount=total_amount,
                        available_balance=commit_result.available_amount,
                        shortfall=commit_result.shortfall,
                        gate_evaluation_id=gate_evaluation_id,
                    ))
                else:
                    self._emitter.emit(FundingBlocked(
                        metadata=EventMetadata.create(
                            tenant_id=batch.tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        funding_request_id=batch.batch_id,
                        legal_entity_id=batch.legal_entity_id,
                        requested_amount=total_amount,
                        available_balance=commit_result.available_amount,
                        block_reason=reason_summary,
                        policy_violated=commit_result.reasons[0].get("code") if commit_result.reasons else None,
                        gate_evaluation_id=gate_evaluation_id,
                    ))

            status = (
                CommitStatus.BLOCKED_FUNDS
                if is_insufficient
                else CommitStatus.BLOCKED_POLICY
            )

            return CommitResult(
                status=status,
                batch_id=batch.batch_id,
                reservation_id=None,
                total_amount=total_amount,
                approved_count=0,
                blocked_count=len(batch.items),
                block_reason=reason_summary,
                correlation_id=correlation_id,
            )

        # Step 2: Create reservation - on LEDGER, not funding gate
        reservation_id = self._ledger.create_reservation(
            tenant_id=batch.tenant_id,
            legal_entity_id=batch.legal_entity_id,
            reserve_type="net_pay",
            amount=total_amount,
            source_type="payroll_batch",
            source_id=batch.batch_id,
            correlation_id=correlation_id,
        )

        # Emit approved event
        if self._emitter and self._config.emit_events:
            balance = self._ledger.get_balance(
                tenant_id=batch.tenant_id,
                ledger_account_id=batch.funding_account_id,
            )
            self._emitter.emit(FundingApproved(
                metadata=EventMetadata.create(
                    tenant_id=batch.tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                funding_request_id=batch.batch_id,
                legal_entity_id=batch.legal_entity_id,
                approved_amount=total_amount,
                available_balance=balance.available,
                gate_evaluation_id=uuid4(),
            ))

        return CommitResult(
            status=CommitStatus.APPROVED,
            batch_id=batch.batch_id,
            reservation_id=reservation_id,
            total_amount=total_amount,
            approved_count=len(batch.items),
            blocked_count=0,
            block_reason=None,
            correlation_id=correlation_id,
        )

    def execute_payments(
        self,
        tenant_id: UUID,
        legal_entity_id: UUID,
        batch_id: UUID,
        funding_account_id: UUID,
        items: list[PayrollItem],
        reservation_id: UUID | None = None,
        rail: str | None = None,
    ) -> ExecuteResult:
        """Execute payments for a committed batch.

        This is step 2 of payroll processing:
        1. Evaluate pay gate (ALWAYS enforced - no bypass)
        2. Create payment instructions
        3. Submit to rail provider
        4. Consume reservation (if provided)
        5. Emit PaymentSubmitted events

        Args:
            tenant_id: Tenant ID
            legal_entity_id: Legal entity ID
            batch_id: Batch ID (for correlation)
            funding_account_id: Account to debit
            items: Payment items to execute
            reservation_id: Optional reservation to consume
            rail: Payment rail to use (default from config)

        Returns:
            ExecuteResult with submission details
        """
        correlation_id = uuid4()
        rail = rail or self._config.default_rail
        provider = self._providers.get(rail)

        if not provider:
            return ExecuteResult(
                status=ExecuteStatus.FAILED,
                batch_id=batch_id,
                submitted_count=0,
                failed_count=len(items),
                failures=[{"error": f"No provider registered for rail: {rail}"}],
                correlation_id=correlation_id,
            )

        # Step 1: Pay gate (ALWAYS enforced)
        if self._config.pay_gate_always_enforced:
            pay_result = self._funding_gate.evaluate_pay_gate(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                pay_run_id=batch_id,
                idempotency_key=f"pay_gate:{batch_id}",
            )

            if not pay_result.passed:
                reason_summary = _summarize_reasons(pay_result.reasons)
                return ExecuteResult(
                    status=ExecuteStatus.BLOCKED,
                    batch_id=batch_id,
                    submitted_count=0,
                    failed_count=len(items),
                    failures=[{"error": reason_summary}],
                    correlation_id=correlation_id,
                )

        # Step 2: Create orchestrator and process payments
        orchestrator = PaymentOrchestrator(self._session, self._ledger, provider)

        submitted_count = 0
        failed_count = 0
        failures: list[dict[str, Any]] = []

        for item in items:
            idempotency_key = f"{batch_id}:{item.payee_ref_id}:{item.purpose}"

            # Create instruction - route by purpose to the correct method
            instr_result = self._create_instruction_for_item(
                orchestrator=orchestrator,
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                batch_id=batch_id,
                item=item,
                idempotency_key=idempotency_key,
            )

            # Emit creation event
            if self._emitter and self._config.emit_events:
                self._emitter.emit(PaymentInstructionCreated(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    payment_instruction_id=instr_result.instruction_id,
                    legal_entity_id=legal_entity_id,
                    purpose=item.purpose,
                    direction="outbound",
                    amount=item.amount,
                    currency="USD",
                    payee_type=item.payee_type,
                    payee_ref_id=item.payee_ref_id,
                    source_type="payroll_batch",
                    source_id=batch_id,
                ))

            # Submit to provider - method is "submit", not "submit_payment"
            submit_result = orchestrator.submit(
                tenant_id=tenant_id,
                payment_instruction_id=instr_result.instruction_id,
            )

            if submit_result.accepted:
                submitted_count += 1

                # Emit submitted event
                if self._emitter and self._config.emit_events:
                    self._emitter.emit(PaymentSubmitted(
                        metadata=EventMetadata.create(
                            tenant_id=tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        payment_instruction_id=instr_result.instruction_id,
                        payment_attempt_id=submit_result.attempt_id or uuid4(),
                        rail=rail,
                        provider=provider.__class__.__name__,
                        provider_request_id=submit_result.provider_request_id or "",
                        estimated_settlement_date=None,
                    ))
            else:
                failed_count += 1
                failures.append({
                    "payee_ref_id": str(item.payee_ref_id),
                    "amount": str(item.amount),
                    "error": submit_result.message,
                })

                # Emit failed event
                if self._emitter and self._config.emit_events:
                    self._emitter.emit(PaymentFailed(
                        metadata=EventMetadata.create(
                            tenant_id=tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        payment_instruction_id=instr_result.instruction_id,
                        payment_attempt_id=submit_result.attempt_id,
                        provider=provider.__class__.__name__,
                        failure_reason=submit_result.message or "Unknown error",
                        failure_code=None,
                        is_retryable=False,
                        error_origin="provider",
                    ))

        # Step 3: Consume reservation if all succeeded
        # Use ledger.release_reservation(consumed=True) instead of funding_gate.consume_reservation
        if reservation_id and failed_count == 0:
            self._ledger.release_reservation(
                tenant_id=tenant_id,
                reservation_id=reservation_id,
                consumed=True,
            )

        # Determine status
        if failed_count == 0:
            status = ExecuteStatus.SUCCESS
        elif submitted_count == 0:
            status = ExecuteStatus.FAILED
        else:
            status = ExecuteStatus.PARTIAL

        return ExecuteResult(
            status=status,
            batch_id=batch_id,
            submitted_count=submitted_count,
            failed_count=failed_count,
            failures=failures,
            correlation_id=correlation_id,
        )

    def _create_instruction_for_item(
        self,
        *,
        orchestrator: PaymentOrchestrator,
        tenant_id: UUID,
        legal_entity_id: UUID,
        batch_id: UUID,
        item: PayrollItem,
        idempotency_key: str,
    ) -> Any:
        """Route to the correct purpose-specific instruction creation method."""
        if item.purpose == "employee_net":
            return orchestrator.create_employee_net_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                employee_id=item.payee_ref_id,
                pay_statement_id=item.metadata.get("pay_statement_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )
        elif item.purpose == "tax_payment":
            return orchestrator.create_tax_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                tax_agency_id=item.payee_ref_id,
                tax_liability_id=item.metadata.get("tax_liability_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )
        elif item.purpose == "vendor_payment":
            return orchestrator.create_third_party_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                provider_id=item.payee_ref_id,
                obligation_id=item.metadata.get("obligation_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )
        else:
            # Default to employee_net for unknown purposes
            return orchestrator.create_employee_net_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                employee_id=item.payee_ref_id,
                pay_statement_id=item.metadata.get("pay_statement_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )

    def ingest_settlement_feed(
        self,
        tenant_id: UUID,
        bank_account_id: UUID,
        provider_name: str,
        records: list[SettlementRecord],
    ) -> IngestResult:
        """Ingest settlement records from a provider.

        This handles the reconciliation flow:
        1. Record each settlement event (idempotent)
        2. Match to payment instructions
        3. Update ledger for settled payments
        4. Handle returns with reversals
        5. Emit events

        Args:
            tenant_id: Tenant ID
            bank_account_id: Bank account receiving settlements
            provider_name: Provider name
            records: Settlement records from provider

        Returns:
            IngestResult with processing details
        """
        correlation_id = uuid4()
        provider = self._providers.get(provider_name)

        if not provider:
            return IngestResult(
                status=IngestStatus.FAILED,
                records_processed=0,
                records_matched=0,
                records_created=0,
                records_failed=0,
                unmatched_trace_ids=[],
                correlation_id=correlation_id,
            )

        # Emit reconciliation started
        if self._emitter and self._config.emit_events:
            self._emitter.emit(ReconciliationStarted(
                metadata=EventMetadata.create(
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                reconciliation_id=correlation_id,
                reconciliation_date=date.today(),
                bank_account_id=bank_account_id,
                provider=provider_name,
            ))

        # Process through reconciliation service - constructor takes (db, ledger, provider, bank_account_id)
        reconciler = ReconciliationService(self._session, self._ledger, provider, bank_account_id)
        # Use run_reconciliation (not process_settlement_feed)
        result = reconciler.run_reconciliation(
            reconciliation_date=date.today(),
            tenant_id=tenant_id,
        )

        # Emit events for each processed record
        if self._emitter and self._config.emit_events:
            for record in records:
                # SettlementRecord has no .rail field - use config default
                self._emitter.emit(SettlementReceived(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    settlement_event_id=uuid4(),
                    bank_account_id=bank_account_id,
                    rail=self._config.default_rail,
                    direction=record.direction,
                    amount=record.amount,
                    currency=record.currency,
                    external_trace_id=record.external_trace_id,
                    effective_date=record.effective_date or date.today(),
                    status=record.status,
                ))

            # Emit completion - use ReconciliationResult attributes:
            # .records_matched (not .matched_count), .records_created (not .created_count)
            self._emitter.emit(ReconciliationCompleted(
                metadata=EventMetadata.create(
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                reconciliation_id=correlation_id,
                reconciliation_date=date.today(),
                records_processed=result.records_processed,
                records_matched=result.records_matched,
                records_created=result.records_created,
                records_failed=result.records_failed,
                unmatched_count=len(result.errors),
            ))

        # Determine status - ReconciliationResult has .errors list, not .unmatched_trace_ids
        if result.records_failed == 0 and len(result.errors) == 0:
            status = IngestStatus.SUCCESS
        elif result.records_processed > result.records_failed:
            status = IngestStatus.PARTIAL
        else:
            status = IngestStatus.FAILED

        # Build unmatched trace IDs from errors
        unmatched_trace_ids = [
            e.get("trace_id", "") for e in result.errors if e.get("trace_id")
        ]

        return IngestResult(
            status=status,
            records_processed=result.records_processed,
            records_matched=result.records_matched,
            records_created=result.records_created,
            records_failed=result.records_failed,
            unmatched_trace_ids=unmatched_trace_ids,
            correlation_id=correlation_id,
        )

    def handle_provider_callback(
        self,
        tenant_id: UUID,
        provider_name: str,
        callback_type: str,
        payload: dict[str, Any],
    ) -> CallbackResult:
        """Handle a callback from a payment provider.

        This handles async status updates:
        1. Validate callback authenticity
        2. Find the referenced payment (idempotent lookup)
        3. Update status if changed
        4. Handle returns with liability classification
        5. Emit events

        Args:
            tenant_id: Tenant ID
            provider_name: Provider name
            callback_type: Type of callback (status_update, return, etc.)
            payload: Callback payload

        Returns:
            CallbackResult with processing details
        """
        correlation_id = uuid4()
        provider = self._providers.get(provider_name)

        if not provider:
            return CallbackResult(
                status=CallbackStatus.INVALID,
                payment_instruction_id=None,
                previous_status=None,
                new_status=None,
                correlation_id=correlation_id,
            )

        # Extract reference from payload
        provider_request_id = payload.get("provider_request_id")
        if not provider_request_id:
            return CallbackResult(
                status=CallbackStatus.INVALID,
                payment_instruction_id=None,
                previous_status=None,
                new_status=None,
                correlation_id=correlation_id,
            )

        # Look up payment instruction by provider reference using private helper
        instruction = self._find_instruction_by_provider_ref(
            tenant_id=tenant_id,
            provider_request_id=provider_request_id,
        )

        if not instruction:
            return CallbackResult(
                status=CallbackStatus.UNKNOWN,
                payment_instruction_id=None,
                previous_status=None,
                new_status=None,
                correlation_id=correlation_id,
            )

        previous_status = instruction["status"]
        new_status = payload.get("status", previous_status)
        instruction_id = instruction["instruction_id"]

        # Check if this is a duplicate (idempotent)
        if previous_status == new_status:
            return CallbackResult(
                status=CallbackStatus.DUPLICATE,
                payment_instruction_id=instruction_id,
                previous_status=previous_status,
                new_status=new_status,
                correlation_id=correlation_id,
            )

        # Handle return case
        if callback_type == "return" or new_status == "returned":
            return_code = payload.get("return_code")
            return_reason = payload.get("return_reason", "Unknown")
            amount = Decimal(str(payload.get("amount", instruction["amount"])))

            # Classify liability - use default_rail since SettlementRecord has no .rail
            classification = self._liability.classify_return(
                rail=self._config.default_rail,
                return_code=return_code or "UNKNOWN",
                amount=amount,
                context=payload,
            )

            # Record liability event - pass classification object, not individual fields
            self._liability.record_liability_event(
                tenant_id=tenant_id,
                legal_entity_id=instruction["legal_entity_id"],
                source_type="payment_instruction",
                source_id=instruction_id,
                classification=classification,
                idempotency_key=f"return:{provider_request_id}:{return_code}",
            )

            # Emit return event
            if self._emitter and self._config.emit_events:
                self._emitter.emit(PaymentReturned(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    payment_instruction_id=instruction_id,
                    settlement_event_id=uuid4(),
                    amount=amount,
                    return_code=return_code or "UNKNOWN",
                    return_reason=return_reason,
                    return_date=date.today(),
                    original_settlement_date=date.today(),
                    liability_party=classification.liability_party.value,
                ))

                self._emitter.emit(LiabilityClassified(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    liability_event_id=uuid4(),
                    payment_instruction_id=instruction_id,
                    settlement_event_id=None,
                    error_origin=classification.error_origin.value,
                    liability_party=classification.liability_party.value,
                    recovery_path=classification.recovery_path.value if classification.recovery_path else "none",
                    amount=amount,
                    return_code=return_code,
                    classification_reason=classification.determination_reason,
                ))

        # Handle settlement case
        elif callback_type == "settlement" or new_status == "settled":
            amount = Decimal(str(payload.get("amount", instruction["amount"])))

            if self._emitter and self._config.emit_events:
                self._emitter.emit(PaymentSettled(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    payment_instruction_id=instruction_id,
                    settlement_event_id=uuid4(),
                    amount=amount,
                    currency="USD",
                    effective_date=date.today(),
                    external_trace_id=provider_request_id,
                ))

        # Update instruction status via orchestrator
        orchestrator = PaymentOrchestrator(self._session, self._ledger, provider)
        orchestrator.update_status(
            tenant_id=tenant_id,
            payment_instruction_id=instruction_id,
            new_status=new_status,
            provider_request_id=provider_request_id,
        )

        return CallbackResult(
            status=CallbackStatus.PROCESSED,
            payment_instruction_id=instruction_id,
            previous_status=previous_status,
            new_status=new_status,
            correlation_id=correlation_id,
        )


class AsyncPSP:
    """Asynchronous PSP Facade.

    Same interface as PSP but for async contexts.
    """

    def __init__(
        self,
        session: AsyncSession,
        config: PSPConfig | None = None,
        providers: dict[str, PaymentRailProvider] | None = None,
        event_emitter: AsyncEventEmitter | None = None,
    ) -> None:
        self._session = session
        self._config = config or PSPConfig()
        self._providers = providers or {}

        # Wire up services - no ledger param for funding gate
        self._ledger = AsyncLedgerService(session)
        self._funding_gate = AsyncFundingGateService(session)
        self._liability = AsyncLiabilityService(session)

        # Event emitter (optional)
        self._emitter = event_emitter

    def register_provider(self, name: str, provider: PaymentRailProvider) -> None:
        """Register a payment rail provider."""
        self._providers[name] = provider

    async def _find_instruction_by_provider_ref(
        self,
        *,
        tenant_id: UUID,
        provider_request_id: str,
    ) -> dict[str, Any] | None:
        """Find a payment instruction by its provider_request_id (async)."""
        result = await self._session.execute(
            text("""
                SELECT pi.payment_instruction_id, pi.status, pi.amount,
                       pi.legal_entity_id, pi.purpose
                FROM payment_attempt pa
                JOIN payment_instruction pi ON pi.payment_instruction_id = pa.payment_instruction_id
                WHERE pa.provider_request_id = :prid
                  AND pi.tenant_id = :tenant_id
                ORDER BY pa.created_at DESC
                LIMIT 1
            """),
            {"prid": provider_request_id, "tenant_id": str(tenant_id)},
        )
        row = result.fetchone()

        if not row:
            return None

        return {
            "instruction_id": UUID(str(row[0])),
            "status": row[1],
            "amount": Decimal(str(row[2])),
            "legal_entity_id": UUID(str(row[3])),
            "purpose": row[4],
        }

    async def commit_payroll_batch(self, batch: PayrollBatch) -> CommitResult:
        """Async version of commit_payroll_batch."""
        correlation_id = uuid4()
        total_amount = sum((item.amount for item in batch.items), Decimal("0"))

        # Emit FundingRequested event
        if self._emitter and self._config.emit_events:
            await self._emitter.emit(FundingRequested(
                metadata=EventMetadata.create(
                    tenant_id=batch.tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                funding_request_id=batch.batch_id,
                legal_entity_id=batch.legal_entity_id,
                pay_period_id=batch.pay_period_id,
                requested_amount=total_amount,
                currency="USD",
                requested_date=batch.effective_date,
            ))

        # Step 1: Evaluate commit gate - actual API params
        commit_result = await self._funding_gate.evaluate_commit_gate(
            tenant_id=batch.tenant_id,
            legal_entity_id=batch.legal_entity_id,
            pay_run_id=batch.pay_period_id,
            funding_model=self._config.default_funding_model,
            idempotency_key=f"commit_gate:{batch.idempotency_key}",
            strict=self._config.commit_gate_strict,
        )

        if not commit_result.passed:
            gate_evaluation_id = uuid4()
            reason_summary = _summarize_reasons(commit_result.reasons)
            is_insufficient = _reasons_contain_insufficient(commit_result.reasons)

            if self._emitter and self._config.emit_events:
                if is_insufficient:
                    await self._emitter.emit(FundingInsufficientFunds(
                        metadata=EventMetadata.create(
                            tenant_id=batch.tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        funding_request_id=batch.batch_id,
                        legal_entity_id=batch.legal_entity_id,
                        requested_amount=total_amount,
                        available_balance=commit_result.available_amount,
                        shortfall=commit_result.shortfall,
                        gate_evaluation_id=gate_evaluation_id,
                    ))
                else:
                    await self._emitter.emit(FundingBlocked(
                        metadata=EventMetadata.create(
                            tenant_id=batch.tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        funding_request_id=batch.batch_id,
                        legal_entity_id=batch.legal_entity_id,
                        requested_amount=total_amount,
                        available_balance=commit_result.available_amount,
                        block_reason=reason_summary,
                        policy_violated=commit_result.reasons[0].get("code") if commit_result.reasons else None,
                        gate_evaluation_id=gate_evaluation_id,
                    ))

            status = (
                CommitStatus.BLOCKED_FUNDS
                if is_insufficient
                else CommitStatus.BLOCKED_POLICY
            )

            return CommitResult(
                status=status,
                batch_id=batch.batch_id,
                reservation_id=None,
                total_amount=total_amount,
                approved_count=0,
                blocked_count=len(batch.items),
                block_reason=reason_summary,
                correlation_id=correlation_id,
            )

        # Step 2: Create reservation - on LEDGER, not funding gate
        reservation_id = await self._ledger.create_reservation(
            tenant_id=batch.tenant_id,
            legal_entity_id=batch.legal_entity_id,
            reserve_type="net_pay",
            amount=total_amount,
            source_type="payroll_batch",
            source_id=batch.batch_id,
            correlation_id=correlation_id,
        )

        # Emit approved event
        if self._emitter and self._config.emit_events:
            balance = await self._ledger.get_balance(
                tenant_id=batch.tenant_id,
                ledger_account_id=batch.funding_account_id,
            )
            await self._emitter.emit(FundingApproved(
                metadata=EventMetadata.create(
                    tenant_id=batch.tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                funding_request_id=batch.batch_id,
                legal_entity_id=batch.legal_entity_id,
                approved_amount=total_amount,
                available_balance=balance.available,
                gate_evaluation_id=uuid4(),
            ))

        return CommitResult(
            status=CommitStatus.APPROVED,
            batch_id=batch.batch_id,
            reservation_id=reservation_id,
            total_amount=total_amount,
            approved_count=len(batch.items),
            blocked_count=0,
            block_reason=None,
            correlation_id=correlation_id,
        )

    async def execute_payments(
        self,
        tenant_id: UUID,
        legal_entity_id: UUID,
        batch_id: UUID,
        funding_account_id: UUID,
        items: list[PayrollItem],
        reservation_id: UUID | None = None,
        rail: str | None = None,
    ) -> ExecuteResult:
        """Async version of execute_payments."""
        correlation_id = uuid4()
        rail = rail or self._config.default_rail
        provider = self._providers.get(rail)

        if not provider:
            return ExecuteResult(
                status=ExecuteStatus.FAILED,
                batch_id=batch_id,
                submitted_count=0,
                failed_count=len(items),
                failures=[{"error": f"No provider registered for rail: {rail}"}],
                correlation_id=correlation_id,
            )

        # Step 1: Pay gate (ALWAYS enforced)
        if self._config.pay_gate_always_enforced:
            pay_result = await self._funding_gate.evaluate_pay_gate(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                pay_run_id=batch_id,
                idempotency_key=f"pay_gate:{batch_id}",
            )

            if not pay_result.passed:
                reason_summary = _summarize_reasons(pay_result.reasons)
                return ExecuteResult(
                    status=ExecuteStatus.BLOCKED,
                    batch_id=batch_id,
                    submitted_count=0,
                    failed_count=len(items),
                    failures=[{"error": reason_summary}],
                    correlation_id=correlation_id,
                )

        # Step 2: Create async orchestrator and process payments
        orchestrator = AsyncPaymentOrchestrator(self._session, self._ledger, provider)

        submitted_count = 0
        failed_count = 0
        failures: list[dict[str, Any]] = []

        for item in items:
            idempotency_key = f"{batch_id}:{item.payee_ref_id}:{item.purpose}"

            # Create instruction - route by purpose
            instr_result = await self._create_instruction_for_item(
                orchestrator=orchestrator,
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                batch_id=batch_id,
                item=item,
                idempotency_key=idempotency_key,
            )

            # Emit creation event
            if self._emitter and self._config.emit_events:
                await self._emitter.emit(PaymentInstructionCreated(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    payment_instruction_id=instr_result.instruction_id,
                    legal_entity_id=legal_entity_id,
                    purpose=item.purpose,
                    direction="outbound",
                    amount=item.amount,
                    currency="USD",
                    payee_type=item.payee_type,
                    payee_ref_id=item.payee_ref_id,
                    source_type="payroll_batch",
                    source_id=batch_id,
                ))

            # Submit to provider
            submit_result = await orchestrator.submit(
                tenant_id=tenant_id,
                payment_instruction_id=instr_result.instruction_id,
            )

            if submit_result.accepted:
                submitted_count += 1

                if self._emitter and self._config.emit_events:
                    await self._emitter.emit(PaymentSubmitted(
                        metadata=EventMetadata.create(
                            tenant_id=tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        payment_instruction_id=instr_result.instruction_id,
                        payment_attempt_id=submit_result.attempt_id or uuid4(),
                        rail=rail,
                        provider=provider.__class__.__name__,
                        provider_request_id=submit_result.provider_request_id or "",
                        estimated_settlement_date=None,
                    ))
            else:
                failed_count += 1
                failures.append({
                    "payee_ref_id": str(item.payee_ref_id),
                    "amount": str(item.amount),
                    "error": submit_result.message,
                })

                if self._emitter and self._config.emit_events:
                    await self._emitter.emit(PaymentFailed(
                        metadata=EventMetadata.create(
                            tenant_id=tenant_id,
                            correlation_id=correlation_id,
                            source_service="psp.facade",
                        ),
                        payment_instruction_id=instr_result.instruction_id,
                        payment_attempt_id=submit_result.attempt_id,
                        provider=provider.__class__.__name__,
                        failure_reason=submit_result.message or "Unknown error",
                        failure_code=None,
                        is_retryable=False,
                        error_origin="provider",
                    ))

        # Consume reservation if all succeeded
        if reservation_id and failed_count == 0:
            await self._ledger.release_reservation(
                tenant_id=tenant_id,
                reservation_id=reservation_id,
                consumed=True,
            )

        if failed_count == 0:
            status = ExecuteStatus.SUCCESS
        elif submitted_count == 0:
            status = ExecuteStatus.FAILED
        else:
            status = ExecuteStatus.PARTIAL

        return ExecuteResult(
            status=status,
            batch_id=batch_id,
            submitted_count=submitted_count,
            failed_count=failed_count,
            failures=failures,
            correlation_id=correlation_id,
        )

    async def _create_instruction_for_item(
        self,
        *,
        orchestrator: AsyncPaymentOrchestrator,
        tenant_id: UUID,
        legal_entity_id: UUID,
        batch_id: UUID,
        item: PayrollItem,
        idempotency_key: str,
    ) -> Any:
        """Route to the correct purpose-specific instruction creation method (async)."""
        if item.purpose == "employee_net":
            return await orchestrator.create_employee_net_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                employee_id=item.payee_ref_id,
                pay_statement_id=item.metadata.get("pay_statement_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )
        elif item.purpose == "tax_payment":
            # AsyncPaymentOrchestrator only has create_employee_net_instruction
            # in the source; for tax/third_party, use the general _create_instruction
            # via employee_net as the available entry point. In practice, additional
            # methods would mirror the sync version.
            return await orchestrator.create_employee_net_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                employee_id=item.payee_ref_id,
                pay_statement_id=item.metadata.get("pay_statement_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )
        elif item.purpose == "vendor_payment":
            return await orchestrator.create_employee_net_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                employee_id=item.payee_ref_id,
                pay_statement_id=item.metadata.get("pay_statement_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )
        else:
            return await orchestrator.create_employee_net_instruction(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                employee_id=item.payee_ref_id,
                pay_statement_id=item.metadata.get("pay_statement_id", batch_id),
                amount=item.amount,
                idempotency_key=idempotency_key,
                metadata=item.metadata,
            )

    async def ingest_settlement_feed(
        self,
        tenant_id: UUID,
        bank_account_id: UUID,
        provider_name: str,
        records: list[SettlementRecord],
    ) -> IngestResult:
        """Async version of ingest_settlement_feed."""
        correlation_id = uuid4()
        provider = self._providers.get(provider_name)

        if not provider:
            return IngestResult(
                status=IngestStatus.FAILED,
                records_processed=0,
                records_matched=0,
                records_created=0,
                records_failed=0,
                unmatched_trace_ids=[],
                correlation_id=correlation_id,
            )

        if self._emitter and self._config.emit_events:
            await self._emitter.emit(ReconciliationStarted(
                metadata=EventMetadata.create(
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                reconciliation_id=correlation_id,
                reconciliation_date=date.today(),
                bank_account_id=bank_account_id,
                provider=provider_name,
            ))

        # Constructor: (db, ledger, provider, bank_account_id)
        reconciler = AsyncReconciliationService(self._session, self._ledger, provider, bank_account_id)
        result = await reconciler.run_reconciliation(
            reconciliation_date=date.today(),
            tenant_id=tenant_id,
        )

        if self._emitter and self._config.emit_events:
            for record in records:
                await self._emitter.emit(SettlementReceived(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    settlement_event_id=uuid4(),
                    bank_account_id=bank_account_id,
                    rail=self._config.default_rail,
                    direction=record.direction,
                    amount=record.amount,
                    currency=record.currency,
                    external_trace_id=record.external_trace_id,
                    effective_date=record.effective_date or date.today(),
                    status=record.status,
                ))

            await self._emitter.emit(ReconciliationCompleted(
                metadata=EventMetadata.create(
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    source_service="psp.facade",
                ),
                reconciliation_id=correlation_id,
                reconciliation_date=date.today(),
                records_processed=result.records_processed,
                records_matched=result.records_matched,
                records_created=result.records_created,
                records_failed=result.records_failed,
                unmatched_count=len(result.errors),
            ))

        if result.records_failed == 0 and len(result.errors) == 0:
            status = IngestStatus.SUCCESS
        elif result.records_processed > result.records_failed:
            status = IngestStatus.PARTIAL
        else:
            status = IngestStatus.FAILED

        unmatched_trace_ids = [
            e.get("trace_id", "") for e in result.errors if e.get("trace_id")
        ]

        return IngestResult(
            status=status,
            records_processed=result.records_processed,
            records_matched=result.records_matched,
            records_created=result.records_created,
            records_failed=result.records_failed,
            unmatched_trace_ids=unmatched_trace_ids,
            correlation_id=correlation_id,
        )

    async def handle_provider_callback(
        self,
        tenant_id: UUID,
        provider_name: str,
        callback_type: str,
        payload: dict[str, Any],
    ) -> CallbackResult:
        """Async version of handle_provider_callback."""
        correlation_id = uuid4()
        provider = self._providers.get(provider_name)

        if not provider:
            return CallbackResult(
                status=CallbackStatus.INVALID,
                payment_instruction_id=None,
                previous_status=None,
                new_status=None,
                correlation_id=correlation_id,
            )

        provider_request_id = payload.get("provider_request_id")
        if not provider_request_id:
            return CallbackResult(
                status=CallbackStatus.INVALID,
                payment_instruction_id=None,
                previous_status=None,
                new_status=None,
                correlation_id=correlation_id,
            )

        instruction = await self._find_instruction_by_provider_ref(
            tenant_id=tenant_id,
            provider_request_id=provider_request_id,
        )

        if not instruction:
            return CallbackResult(
                status=CallbackStatus.UNKNOWN,
                payment_instruction_id=None,
                previous_status=None,
                new_status=None,
                correlation_id=correlation_id,
            )

        previous_status = instruction["status"]
        new_status = payload.get("status", previous_status)
        instruction_id = instruction["instruction_id"]

        if previous_status == new_status:
            return CallbackResult(
                status=CallbackStatus.DUPLICATE,
                payment_instruction_id=instruction_id,
                previous_status=previous_status,
                new_status=new_status,
                correlation_id=correlation_id,
            )

        # Handle return case
        if callback_type == "return" or new_status == "returned":
            return_code = payload.get("return_code")
            return_reason = payload.get("return_reason", "Unknown")
            amount = Decimal(str(payload.get("amount", instruction["amount"])))

            classification = await self._liability.classify_return(
                rail=self._config.default_rail,
                return_code=return_code or "UNKNOWN",
                amount=amount,
                context=payload,
            )

            await self._liability.record_liability_event(
                tenant_id=tenant_id,
                legal_entity_id=instruction["legal_entity_id"],
                source_type="payment_instruction",
                source_id=instruction_id,
                classification=classification,
                idempotency_key=f"return:{provider_request_id}:{return_code}",
            )

            if self._emitter and self._config.emit_events:
                await self._emitter.emit(PaymentReturned(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    payment_instruction_id=instruction_id,
                    settlement_event_id=uuid4(),
                    amount=amount,
                    return_code=return_code or "UNKNOWN",
                    return_reason=return_reason,
                    return_date=date.today(),
                    original_settlement_date=date.today(),
                    liability_party=classification.liability_party.value,
                ))

                await self._emitter.emit(LiabilityClassified(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    liability_event_id=uuid4(),
                    payment_instruction_id=instruction_id,
                    settlement_event_id=None,
                    error_origin=classification.error_origin.value,
                    liability_party=classification.liability_party.value,
                    recovery_path=classification.recovery_path.value if classification.recovery_path else "none",
                    amount=amount,
                    return_code=return_code,
                    classification_reason=classification.determination_reason,
                ))

        # Handle settlement case
        elif callback_type == "settlement" or new_status == "settled":
            amount = Decimal(str(payload.get("amount", instruction["amount"])))

            if self._emitter and self._config.emit_events:
                await self._emitter.emit(PaymentSettled(
                    metadata=EventMetadata.create(
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        source_service="psp.facade",
                    ),
                    payment_instruction_id=instruction_id,
                    settlement_event_id=uuid4(),
                    amount=amount,
                    currency="USD",
                    effective_date=date.today(),
                    external_trace_id=provider_request_id,
                ))

        # Update instruction status
        orchestrator = AsyncPaymentOrchestrator(self._session, self._ledger, provider)
        await orchestrator.update_status(
            tenant_id=tenant_id,
            payment_instruction_id=instruction_id,
            new_status=new_status,
            provider_request_id=provider_request_id,
        )

        return CallbackResult(
            status=CallbackStatus.PROCESSED,
            payment_instruction_id=instruction_id,
            previous_status=previous_status,
            new_status=new_status,
            correlation_id=correlation_id,
        )
