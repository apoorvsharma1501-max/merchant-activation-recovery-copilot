"""AI classification of blank-code (or invalid-code) reviewer text against the catalog.

The model only proposes a catalog code with an exact evidence quote. Code checks then:
  - the code must be in the catalog (or UNKNOWN),
  - the quote must appear verbatim in the reviewer text,
  - the deterministic sensitive-word guard can only ADD caution, never remove it.
Anything that fails validation (after one repair retry) goes to human review.
"""
from __future__ import annotations

from dataclasses import replace

from pydantic import ValidationError

import config
from core import rules
from core.data_loader import CatalogEntry
from core.llm_client import CachedLLM, load_prompt
from schemas.diagnosis_schema import AIDiagnosis, diagnosis_json_schema
from schemas.labels import CODE_NEEDS_HUMAN_REVIEW, CODE_UNKNOWN, DiagnosisMethod, DiagnosisStatus


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def build_user_prompt(message: str, catalog: dict[str, CatalogEntry]) -> str:
    lines = ["Catalog (code | reviewer reason | plain meaning):"]
    for code in sorted(catalog):
        e = catalog[code]
        lines.append(f"{code} | {e.reviewer_reason} | {e.plain_language_meaning}")
    lines += ["", "Reviewer note:", "<<<", message, ">>>"]
    return "\n".join(lines)


def validate(data: dict | None, message: str, catalog: dict[str, CatalogEntry]) -> tuple[AIDiagnosis | None, str]:
    """Return (parsed diagnosis, "") or (None, reason it was rejected)."""
    if data is None:
        return None, "no JSON returned"
    try:
        ai = AIDiagnosis.model_validate(data)
    except ValidationError as e:
        return None, f"schema validation failed: {e.errors()[0]['msg']}"
    code = ai.diagnosed_reason_code.strip().upper()
    if code != CODE_UNKNOWN and code not in catalog:
        return None, f"code {code!r} is not in the catalog"
    if code != CODE_UNKNOWN:
        quote = _normalize_ws(ai.evidence_quote)
        if not quote:
            return None, "evidence_quote is empty"
        if quote not in _normalize_ws(message):
            return None, "evidence_quote is not an exact substring of the reviewer text"
    return ai.model_copy(update={"diagnosed_reason_code": code}), ""


def classify(row: dict, rule_dx: rules.Diagnosis, catalog: dict[str, CatalogEntry],
             llm: CachedLLM) -> rules.Diagnosis:
    """Upgrade a rule diagnosis that is `pending_ai`. Returns the rule diagnosis unchanged
    (with a note) when AI is unavailable."""
    message = row["rejection_message"]
    invalid_original_code = bool(row.get("rejection_code"))
    guard_sensitive = rules.is_sensitive_text(message)
    system = load_prompt("diagnosis_system.txt")
    base_prompt = build_user_prompt(message, catalog)
    schema = diagnosis_json_schema(sorted(catalog))
    pv = config.DIAGNOSIS_PROMPT_VERSION

    ai, failure, model = None, "", llm.model
    for attempt in range(2):
        prompt = base_prompt if attempt == 0 else (
            f"{base_prompt}\n\nYour previous answer was rejected: {failure}. "
            "Answer again following every rule; copy evidence_quote exactly from the note.")
        res = llm.complete_json(system, prompt, schema, config.LLM_EFFORT_DIAGNOSIS)
        model = res.model
        if res.status == "unavailable":
            return replace(rule_dx, review_reasons=rule_dx.review_reasons + (f"AI unavailable: {res.detail}",))
        if res.status == "refusal":
            failure = "model declined"
            break
        if res.status != "ok":
            failure = f"{res.status}: {res.detail}"
            continue
        ai, failure = validate(res.data, message, catalog)
        if ai:
            break

    if ai is None:
        return replace(rule_dx, model=model, prompt_version=pv, sensitive=rule_dx.sensitive or guard_sensitive,
                       review_reasons=rule_dx.review_reasons + (f"AI diagnosis rejected: {failure}",))

    sensitive = guard_sensitive or ai.sensitive_case
    reasons: list[str] = []
    if invalid_original_code:
        reasons.append(f"Original code {row['rejection_code']!r} not in catalog; AI suggestion needs confirmation")
    if ai.needs_human_review:
        reasons.append("AI flagged the note as ambiguous")
    if sensitive:
        reasons.append("Sensitive wording; merchant-facing detail withheld until a human confirms")
    evidence = f'"{ai.evidence_quote}"' if ai.evidence_quote else message

    if ai.diagnosed_reason_code == CODE_UNKNOWN:
        return rules.Diagnosis(CODE_UNKNOWN, DiagnosisStatus.UNKNOWN, DiagnosisMethod.LLM_TEXT_CLASSIFICATION,
                               message, True, tuple(reasons + ["No catalog reason supported by the note"]),
                               sensitive=sensitive, model=model, prompt_version=pv,
                               ai_explanation=ai.explanation)

    return rules.Diagnosis(ai.diagnosed_reason_code, DiagnosisStatus.AI_CLASSIFIED,
                           DiagnosisMethod.LLM_TEXT_CLASSIFICATION, evidence, bool(reasons), tuple(reasons),
                           sensitive=sensitive, model=model, prompt_version=pv, ai_explanation=ai.explanation)


def check_consistency(row: dict, rule_dx: rules.Diagnosis, catalog: dict[str, CatalogEntry],
                      llm: CachedLLM) -> rules.Diagnosis:
    """Handover §5.2 Rule 1: a known code is kept, but if the reviewer text clearly points to a
    DIFFERENT catalog reason, the row goes to human review (original code retained).

    The AI reads the text exactly as for blank-code rows (same prompt, so answers are shared via the
    cache). It never replaces the code. If the AI is unavailable, fails validation or returns UNKNOWN,
    the rule diagnosis stands unchanged - this check can only add caution.
    """
    probe = dict(row, rejection_code=None)  # classify the text on its own
    ai_dx = classify(probe, rules.diagnose(probe, catalog), catalog, llm)
    if ai_dx.method is not DiagnosisMethod.LLM_TEXT_CLASSIFICATION or ai_dx.code in (CODE_UNKNOWN, rule_dx.code):
        return rule_dx
    reason = (f"Reviewer text suggests {ai_dx.code} ({catalog[ai_dx.code].reviewer_reason}), "
              f"not the recorded {rule_dx.code}: {ai_dx.evidence}")
    return replace(rule_dx, status=DiagnosisStatus.NEEDS_HUMAN_REVIEW, human_review=True,
                   review_reasons=rule_dx.review_reasons + (reason,), sensitive=rule_dx.sensitive or ai_dx.sensitive,
                   model=ai_dx.model, prompt_version=ai_dx.prompt_version, ai_explanation=ai_dx.ai_explanation)


__all__ = ["classify", "check_consistency", "validate", "build_user_prompt", "CODE_NEEDS_HUMAN_REVIEW"]
