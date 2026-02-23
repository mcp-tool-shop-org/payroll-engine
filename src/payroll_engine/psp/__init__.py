"""PSP (Payment Service Provider) operations package.

This package contains services for:
- Ledger operations (append-only double-entry)
- Funding gate evaluations
- Payment orchestration
- Rail provider adapters
- Reconciliation jobs
- Liability attribution
- Domain events
"""

from payroll_engine.psp.config import FundingGateConfig, LedgerConfig, PSPConfig
from payroll_engine.psp.events import (
    AsyncEventEmitter,
    AsyncEventHandler,
    AsyncEventStore,
    # Base types
    DomainEvent,
    EventCategory,
    # Event emitter
    EventEmitter,
    EventHandler,
    EventMetadata,
    # Event store
    EventStore,
    FundingApproved,
    FundingBlocked,
    FundingInsufficientFunds,
    # Funding events
    FundingRequested,
    # Ledger events
    LedgerEntryPosted,
    LedgerEntryReversed,
    # Liability events
    LiabilityClassified,
    LiabilityRecovered,
    LiabilityRecoveryStarted,
    LiabilityWrittenOff,
    PaymentAccepted,
    PaymentCanceled,
    PaymentFailed,
    # Payment events
    PaymentInstructionCreated,
    PaymentReturned,
    PaymentSettled,
    PaymentSubmitted,
    ReconciliationCompleted,
    ReconciliationFailed,
    # Reconciliation events
    ReconciliationStarted,
    SettlementMatched,
    # Settlement events
    SettlementReceived,
    SettlementStatusChanged,
    SettlementUnmatched,
    StoredEvent,
)
from payroll_engine.psp.providers.ach_stub import AchStubProvider
from payroll_engine.psp.providers.base import (
    CancelResult,
    PaymentRailProvider,
    RailCapabilities,
    SettlementRecord,
    StatusResult,
)
from payroll_engine.psp.providers.base import (
    SubmitResult as ProviderSubmitResult,
)
from payroll_engine.psp.providers.fednow_stub import FedNowStubProvider
from payroll_engine.psp.psp import PSP
from payroll_engine.psp.services import (
    AsyncFundingGateService,
    AsyncLedgerService,
    AsyncPaymentOrchestrator,
    AsyncReconciliationService,
    Balance,
    # Funding Gate
    FundingGateService,
    FundingRequirement,
    GateResult,
    InstructionResult,
    # Ledger
    LedgerService,
    # Payment Orchestrator
    PaymentOrchestrator,
    PostResult,
    ReconciliationResult,
    # Reconciliation
    ReconciliationService,
    SubmissionResult,
)
from payroll_engine.psp.services.liability import (
    AsyncLiabilityService,
    ErrorOrigin,
    LiabilityClassification,
    LiabilityEvent,
    LiabilityParty,
    LiabilityService,
    RecoveryPath,
    RecoveryStatus,
)

__all__ = [
    # PSP Core
    "PSP",
    "PSPConfig",
    "LedgerConfig",
    "FundingGateConfig",
    # Ledger Service
    "LedgerService",
    "AsyncLedgerService",
    "Balance",
    "PostResult",
    # Funding Gate
    "FundingGateService",
    "AsyncFundingGateService",
    "GateResult",
    "FundingRequirement",
    # Payment Orchestrator
    "PaymentOrchestrator",
    "AsyncPaymentOrchestrator",
    "InstructionResult",
    "SubmissionResult",
    # Reconciliation
    "ReconciliationService",
    "AsyncReconciliationService",
    "ReconciliationResult",
    # Liability
    "LiabilityService",
    "AsyncLiabilityService",
    "LiabilityClassification",
    "LiabilityEvent",
    "ErrorOrigin",
    "LiabilityParty",
    "RecoveryPath",
    "RecoveryStatus",
    # Provider Protocol and Types
    "PaymentRailProvider",
    "RailCapabilities",
    "ProviderSubmitResult",
    "StatusResult",
    "CancelResult",
    "SettlementRecord",
    # Stub Providers
    "AchStubProvider",
    "FedNowStubProvider",
    # Events - Base
    "DomainEvent",
    "EventMetadata",
    "EventCategory",
    # Events - Emitter
    "EventEmitter",
    "AsyncEventEmitter",
    "EventHandler",
    "AsyncEventHandler",
    # Events - Store
    "EventStore",
    "AsyncEventStore",
    "StoredEvent",
    # Events - Funding
    "FundingRequested",
    "FundingApproved",
    "FundingBlocked",
    "FundingInsufficientFunds",
    # Events - Payment
    "PaymentInstructionCreated",
    "PaymentSubmitted",
    "PaymentAccepted",
    "PaymentSettled",
    "PaymentFailed",
    "PaymentReturned",
    "PaymentCanceled",
    # Events - Ledger
    "LedgerEntryPosted",
    "LedgerEntryReversed",
    # Events - Settlement
    "SettlementReceived",
    "SettlementMatched",
    "SettlementUnmatched",
    "SettlementStatusChanged",
    # Events - Liability
    "LiabilityClassified",
    "LiabilityRecoveryStarted",
    "LiabilityRecovered",
    "LiabilityWrittenOff",
    # Events - Reconciliation
    "ReconciliationStarted",
    "ReconciliationCompleted",
    "ReconciliationFailed",
]
