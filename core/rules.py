"""Deterministic decision engine: eligibility, diagnosis, recoverability, channel.

No LLM is used here. Blank-code reviewer text is NOT guessed by rules: it is marked
`pending_ai` and sent to human review until the Phase 3 classifier (or a person) decides.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import config
from core.data_loader import CatalogEntry
from schemas.labels import (
    CODE_NEEDS_HUMAN_REVIEW, DiagnosisMethod, DiagnosisStatus, Fixability,
    LanguageStatus, Recoverability, RecommendedAction,
)

_SENSITIVE_RE = re.compile("|".join(config.SENSITIVE_TEXT_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class Diagnosis:
    code: str  # catalog code, UNKNOWN or NEEDS_HUMAN_REVIEW
    status: DiagnosisStatus
    method: DiagnosisMethod
    evidence: str
    human_review: bool
    review_reasons: tuple[str, ...] = ()
    sensitive: bool = False      # restricted/compliance wording: suppress merchant-facing detail
    pending_ai: bool = False     # reviewer text exists that rules do not interpret
    model: str = "RULE_ONLY"
    prompt_version: str = "N/A"
    ai_explanation: str = ""     # model's one-line reason, shown to reviewers only


@dataclass(frozen=True)
class Decision:
    fixability: Fixability
    recoverability: Recoverability
    action: RecommendedAction
    human_review: bool
    review_reasons: tuple[str, ...] = field(default_factory=tuple)


# --- Eligibility ---------------------------------------------------------------

def is_in_scope(status: str | None) -> bool:
    """Every non-activated record is in scope, including unknown/missing statuses
    (those are kept and flagged rather than silently dropped)."""
    return status != config.STATUS_ACTIVATED


def is_sensitive_text(text: str | None) -> bool:
    return bool(text) and bool(_SENSITIVE_RE.search(text))


# --- Diagnosis -----------------------------------------------------------------

def diagnose(row: dict, catalog: dict[str, CatalogEntry]) -> Diagnosis:
    code = row.get("rejection_code")
    message = row.get("rejection_message")
    status = row.get("application_status")
    step = row.get("step_reached")
    reasons: list[str] = []
    if status not in config.KNOWN_STATUSES:
        reasons.append(f"Unrecognized application status {status!r}")

    # Rule 1: known catalog code -> use it as given.
    if code and code in catalog:
        evidence = message or f"Rejection code {code} recorded; no reviewer text"
        return Diagnosis(code, DiagnosisStatus.KNOWN_CODE, DiagnosisMethod.CATALOG_RULE,
                         evidence, human_review=bool(reasons), review_reasons=tuple(reasons))

    # Rule 4: code present but not in catalog -> keep original, human review.
    if code:
        reasons.append(f"Rejection code {code!r} is not in the catalog")
        sensitive = is_sensitive_text(message)
        if sensitive:
            reasons.append("Reviewer text suggests restricted-category/compliance issue")
        return Diagnosis(CODE_NEEDS_HUMAN_REVIEW, DiagnosisStatus.NEEDS_HUMAN_REVIEW,
                         DiagnosisMethod.HUMAN_REVIEW, message or "", True, tuple(reasons),
                         sensitive=sensitive, pending_ai=bool(message))

    # Rule 2: blank code + reviewer text -> needs text classification (Phase 3 / human).
    if message:
        sensitive = is_sensitive_text(message)
        reasons.append("Blank code; reviewer text needs classification (AI diagnosis not run)")
        if sensitive:
            reasons.append("Reviewer text suggests restricted-category/compliance issue; "
                           "merchant-facing diagnosis suppressed")
        return Diagnosis(CODE_NEEDS_HUMAN_REVIEW, DiagnosisStatus.NEEDS_HUMAN_REVIEW,
                         DiagnosisMethod.HUMAN_REVIEW, message, True, tuple(reasons),
                         sensitive=sensitive, pending_ai=True)

    # Rule 3: no code, no text.
    if status == config.STATUS_STALLED and step and step != config.STATUS_ACTIVATED \
            and config.INACTIVITY_CODE in catalog and not reasons:
        days = row.get("days_since_last_activity")
        days_txt = f"{days:g} days since last activity" if days is not None else "days since activity missing"
        evidence = (f"Status 'Stalled' with no rejection code or reviewer text; "
                    f"last step reached '{step}'; {days_txt}")
        return Diagnosis(config.INACTIVITY_CODE, DiagnosisStatus.INACTIVITY_INFERRED,
                         DiagnosisMethod.INACTIVITY_RULE, evidence, human_review=False)

    if status == config.STATUS_REJECTED:
        reasons.append("Rejected with no rejection code or reviewer text; do not assume inactivity")
    elif status == config.STATUS_STALLED and not step:
        reasons.append("Stalled with no step_reached; cannot name where the merchant stopped")
    elif config.INACTIVITY_CODE not in catalog:
        reasons.append(f"Inactivity code {config.INACTIVITY_CODE} missing from catalog")
    return Diagnosis(CODE_NEEDS_HUMAN_REVIEW, DiagnosisStatus.NEEDS_HUMAN_REVIEW,
                     DiagnosisMethod.HUMAN_REVIEW, "No rejection evidence", True, tuple(reasons))


# --- Recoverability -------------------------------------------------------------

def decide(diagnosis: Diagnosis, catalog: dict[str, CatalogEntry]) -> Decision:
    """Map a diagnosis to fixability/recoverability using the catalog's `fixable` value.
    Fixability (what the catalog says) and recoverability (what we do) stay separate."""
    entry = catalog.get(diagnosis.code)
    reasons = diagnosis.review_reasons
    if diagnosis.status in (DiagnosisStatus.NEEDS_HUMAN_REVIEW, DiagnosisStatus.UNKNOWN) or entry is None:
        return Decision(Fixability.UNKNOWN, Recoverability.NEEDS_HUMAN_REVIEW,
                        RecommendedAction.HUMAN_REVIEW, True, reasons)

    fx = entry.fixability
    if fx is Fixability.NO:
        return Decision(fx, Recoverability.NOT_RECOVERABLE_CLOSE, RecommendedAction.CLOSE_POLITELY,
                        diagnosis.human_review, reasons)
    if fx is Fixability.NEEDS_COMPLIANCE_REVIEW:
        return Decision(fx, Recoverability.COMPLIANCE_REVIEW, RecommendedAction.COMPLIANCE_ROUTE,
                        diagnosis.human_review, reasons)
    if fx is Fixability.YES:
        if diagnosis.sensitive:
            # Fixable code but sensitive wording: never send ordinary fix advice unreviewed.
            return Decision(fx, Recoverability.NEEDS_HUMAN_REVIEW, RecommendedAction.HUMAN_REVIEW,
                            True, reasons + ("Sensitive wording on a fixable code",))
        if diagnosis.method is DiagnosisMethod.LLM_TEXT_CLASSIFICATION and diagnosis.human_review:
            # The AI suggested a fixable code but is not sure (or the original code was invalid).
            # Keep the suggestion visible, but do not count it as recoverable, rank it, or message it
            # until a person confirms.
            return Decision(fx, Recoverability.NEEDS_HUMAN_REVIEW, RecommendedAction.HUMAN_REVIEW,
                            True, reasons + ("AI diagnosis needs human confirmation before outreach",))
        action =(RecommendedAction.REMINDER_NUDGE if diagnosis.code == config.INACTIVITY_CODE
                  else RecommendedAction.CORRECTIVE_NUDGE)
        return Decision(fx, Recoverability.RECOVERABLE, action, diagnosis.human_review, reasons)
    return Decision(Fixability.UNKNOWN, Recoverability.NEEDS_HUMAN_REVIEW, RecommendedAction.HUMAN_REVIEW,
                    True, reasons + (f"Catalog fixable value for {diagnosis.code} is unrecognized",))


# --- Channel and language ----------------------------------------------------

def select_channel(whatsapp_allowed: bool, recoverability: Recoverability) -> str:
    """WhatsApp only on explicit opt-in. Compliance cases are never auto-channelled to WhatsApp."""
    if recoverability is Recoverability.NEEDS_HUMAN_REVIEW:
        return config.CHANNEL_NOT_APPLICABLE
    if recoverability is Recoverability.COMPLIANCE_REVIEW:
        return config.CHANNEL_MANUAL
    return config.CHANNEL_WHATSAPP if whatsapp_allowed else config.CHANNEL_MANUAL


def language_for(preferred: str | None) -> tuple[str, LanguageStatus]:
    if preferred in config.SUPPORTED_LANGUAGES:
        return preferred, LanguageStatus.OK
    return "English (fallback - not merchant's preferred language)", LanguageStatus.NEEDS_REVIEW


# --- Message brief (what Phase 3 may say; the LLM only localizes it) ---------

COMPLIANCE_NEUTRAL_MESSAGE = ("Your application is currently under review. Our team will contact you "
                              "if any further information is required. Thank you for your patience.")


def message_brief(decision: Decision, diagnosis: Diagnosis, entry: CatalogEntry | None,
                  step: str | None) -> str:
    action = decision.action
    if action is RecommendedAction.HUMAN_REVIEW or (diagnosis.human_review and diagnosis.sensitive):
        return "No merchant message until a human confirms the diagnosis."
    if action is RecommendedAction.COMPLIANCE_ROUTE:
        return f"Neutral wording only, no reason or code: \"{COMPLIANCE_NEUTRAL_MESSAGE}\""
    if action is RecommendedAction.CLOSE_POLITELY:
        return ("Politely tell the merchant we cannot support this business category and the application "
                "is closed. Do not suggest any workaround, category change or alternative route.")
    if action is RecommendedAction.REMINDER_NUDGE:
        return (f"Friendly reminder: the merchant stopped at the '{step}' step. Ask them to sign in to "
                f"their onboarding account and continue from the '{step}' step. No resume link exists "
                f"in the data - do not include or invent one. No timeline or approval promise.")
    return (f"Issue (catalog): {entry.plain_language_meaning} | Approved fix (catalog): {entry.standard_fix} "
            f"| No timeline or approval promise.")
