"""Draft merchant messages.

The rule engine decides WHAT may be said (the brief). The LLM only expresses the
brief in the merchant's language; every draft is safety-checked and still needs
human approval. Nothing is ever sent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ValidationError

import config
from core import nudge_safety, rules
from core.data_loader import CatalogEntry
from core.llm_client import CachedLLM, load_prompt
from schemas.diagnosis_schema import NUDGE_JSON_SCHEMA, NudgeDraft
from schemas.labels import (
    DiagnosisMethod, LanguageStatus, NudgeStatus, Recoverability, RecommendedAction,
)


@dataclass
class NudgeResult:
    text: str | None
    back_translation: str | None
    status: NudgeStatus
    safety_passed: bool | None
    issues: list[str] = field(default_factory=list)
    model: str = "N/A"
    prompt_version: str = "N/A"


def should_withhold(dx: rules.Diagnosis, dec: rules.Decision) -> bool:
    """No merchant message until a human confirms: undetermined, sensitive or AI-uncertain cases."""
    if dec.recoverability is Recoverability.NEEDS_HUMAN_REVIEW:
        return True
    if dx.sensitive and dec.human_review:
        return True
    return dx.method is DiagnosisMethod.LLM_TEXT_CLASSIFICATION and dec.human_review


def build_brief(dec: rules.Decision, entry: CatalogEntry | None, step: str | None, language: str) -> str:
    lines = [f"Language: {language}"]
    if dec.action is RecommendedAction.COMPLIANCE_ROUTE:
        lines += ["Message type: fixed neutral text. Translate exactly, add nothing:",
                  rules.COMPLIANCE_NEUTRAL_MESSAGE]
    elif dec.action is RecommendedAction.CLOSE_POLITELY:
        lines += ["Message type: closure.",
                  "Say politely that we are unable to support this business category, so the application "
                  "has been closed, and thank them. Say nothing else."]
    elif dec.action is RecommendedAction.REMINDER_NUDGE:
        lines += ["Message type: friendly reminder (there was no rejection).",
                  f"Where they stopped: the '{step}' step.",
                  f"Ask them to sign in to their onboarding account and continue from the '{step}' step."]
    else:
        lines += ["Message type: fix needed to continue onboarding.",
                  f"Where they stopped: the '{step}' step.",
                  f"What went wrong (approved wording): {entry.plain_language_meaning}",
                  f"What to do (approved wording): {entry.standard_fix}",
                  "Then ask them to sign in to their onboarding account and resubmit."]
    return "\n".join(lines)


def english_template(dec: rules.Decision, entry: CatalogEntry | None, step: str | None) -> str:
    """Deterministic English fallback when AI is unavailable. Uses only catalog wording."""
    if dec.action is RecommendedAction.COMPLIANCE_ROUTE:
        return rules.COMPLIANCE_NEUTRAL_MESSAGE
    if dec.action is RecommendedAction.CLOSE_POLITELY:
        return ("Hello. Thank you for your interest. We are unable to support this business category, "
                "so your application has been closed. Thank you for your understanding.")
    if dec.action is RecommendedAction.REMINDER_NUDGE:
        return (f"Hello! Your onboarding is paused at the {step} step. Please sign in to your onboarding "
                f"account and continue from the {step} step. Thank you!")
    return (f"Hello! Your onboarding is paused at the {step} step. {entry.plain_language_meaning} "
            f"To continue: {entry.standard_fix} Then please sign in to your onboarding account and "
            f"resubmit. Thank you!")


def generate(row: dict, dx: rules.Diagnosis, dec: rules.Decision, entry: CatalogEntry | None,
             llm: CachedLLM | None) -> NudgeResult:
    if should_withhold(dx, dec):
        return NudgeResult(None, None, NudgeStatus.NO_NUDGE_HUMAN_REVIEW, None)

    step = row.get("step_reached")
    language, lang_status = rules.language_for(row.get("preferred_language"))
    target = language if lang_status is LanguageStatus.OK else "English"
    extra = [] if lang_status is LanguageStatus.OK else ["preferred language unsupported; English fallback"]
    ok_status = (NudgeStatus.NEUTRAL_COMPLIANCE if dec.action is RecommendedAction.COMPLIANCE_ROUTE
                 else NudgeStatus.DRAFTED)
    brief = build_brief(dec, entry, step, target)

    def _checked(text: str, back: str, model: str, pv: str) -> NudgeResult:
        issues = nudge_safety.check(text, back, target, dec.action, brief, step, dx.sensitive)
        status = ok_status if not issues else NudgeStatus.NO_NUDGE_HUMAN_REVIEW
        return NudgeResult(text, back, status, not issues, extra + issues, model, pv)

    # English compliance text is fixed: no model needed.
    if dec.action is RecommendedAction.COMPLIANCE_ROUTE and target == "English":
        msg = rules.COMPLIANCE_NEUTRAL_MESSAGE
        return _checked(msg, msg, "RULE_TEMPLATE", "N/A")

    if llm is not None and llm.enabled:
        system = load_prompt("nudge_system.txt")
        pv = config.NUDGE_PROMPT_VERSION
        prompt, last, failure = brief, None, ""
        for _ in range(2):
            res = llm.complete_json(system, prompt, NUDGE_JSON_SCHEMA, config.LLM_EFFORT_NUDGE)
            if res.status == "unavailable":
                failure = f"AI unavailable: {res.detail}"
                break
            if res.status != "ok":
                failure = f"AI {res.status}: {res.detail}"
                if res.status == "refusal":
                    break
                continue
            try:
                draft = NudgeDraft.model_validate(res.data)
            except ValidationError as e:
                failure = f"schema validation failed: {e.errors()[0]['msg']}"
                continue
            last = _checked(draft.message, draft.english_back_translation, res.model, pv)
            if last.safety_passed:
                return last
            failure = "; ".join(last.issues)
            prompt = (f"{brief}\n\nA previous draft was rejected by automatic checks: {failure}. "
                      "Write it again and fix those problems.")
        if last is not None:
            return last  # keeps the failed draft visible to reviewers, marked not safe
        if not failure.startswith("AI unavailable"):
            return NudgeResult(None, None, NudgeStatus.NO_NUDGE_HUMAN_REVIEW, None, extra + [failure])

    if target == "English":
        text = english_template(dec, entry, step)
        return _checked(text, text, "RULE_TEMPLATE", "N/A")
    return NudgeResult(None, None, NudgeStatus.NOT_GENERATED, None,
                       extra + [f"AI unavailable; no approved {target} template"])
