"""Controlled vocabularies used in every output row (handover sections 5-7)."""
from enum import StrEnum

CODE_UNKNOWN = "UNKNOWN"
CODE_NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class DiagnosisStatus(StrEnum):
    KNOWN_CODE = "KNOWN_CODE"
    AI_CLASSIFIED = "AI_CLASSIFIED"
    INACTIVITY_INFERRED = "INACTIVITY_INFERRED"
    UNKNOWN = "UNKNOWN"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class DiagnosisMethod(StrEnum):
    CATALOG_RULE = "CATALOG_RULE"
    LLM_TEXT_CLASSIFICATION = "LLM_TEXT_CLASSIFICATION"
    INACTIVITY_RULE = "INACTIVITY_RULE"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class Fixability(StrEnum):
    """Mirrors the catalog's `fixable` column; 'Needs compliance review' is kept distinct."""
    YES = "Yes"
    NO = "No"
    NEEDS_COMPLIANCE_REVIEW = "Needs compliance review"
    UNKNOWN = "Unknown"


class Recoverability(StrEnum):
    RECOVERABLE = "RECOVERABLE"
    NOT_RECOVERABLE_CLOSE = "NOT_RECOVERABLE_CLOSE"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class RecommendedAction(StrEnum):
    CORRECTIVE_NUDGE = "Corrective nudge"
    REMINDER_NUDGE = "Reminder nudge"
    CLOSE_POLITELY = "Close politely (no workaround)"
    COMPLIANCE_ROUTE = "Route to Compliance (neutral message only)"
    HUMAN_REVIEW = "Human review"


class NudgeStatus(StrEnum):
    DRAFTED = "DRAFTED"
    NEUTRAL_COMPLIANCE = "NEUTRAL_COMPLIANCE"
    NO_NUDGE_HUMAN_REVIEW = "NO_NUDGE_HUMAN_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    # Phase 2 placeholder: a message brief exists but text is drafted in Phase 3.
    NOT_GENERATED = "NOT_GENERATED"


class LanguageStatus(StrEnum):
    OK = "OK"
    NEEDS_REVIEW = "NEEDS_REVIEW"
