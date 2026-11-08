"""Deterministic diagnosis, recoverability and channel rules."""
import pytest

import config
from core import rules
from evaluation.test_data import make_row
from schemas.labels import (
    CODE_NEEDS_HUMAN_REVIEW, DiagnosisMethod, DiagnosisStatus, Fixability,
    Recoverability, RecommendedAction,
)

FIXABLE_CORRECTIVE = ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R11"]


@pytest.mark.parametrize("code", FIXABLE_CORRECTIVE)
def test_fixable_codes_map_to_corrective_nudge(code, catalog):
    dx = rules.diagnose(make_row(rejection_code=code, rejection_message="reviewer note"), catalog)
    assert (dx.code, dx.status, dx.method) == (code, DiagnosisStatus.KNOWN_CODE, DiagnosisMethod.CATALOG_RULE)
    assert dx.evidence == "reviewer note" and not dx.human_review
    dec = rules.decide(dx, catalog)
    assert dec.fixability is Fixability.YES
    assert dec.recoverability is Recoverability.RECOVERABLE
    assert dec.action is RecommendedAction.CORRECTIVE_NUDGE
    brief = rules.message_brief(dec, dx, catalog[code], "KYC docs")
    assert catalog[code].standard_fix in brief  # fix text comes from the catalog, verbatim


def test_known_code_without_text_still_uses_catalog(catalog):
    dx = rules.diagnose(make_row(rejection_code="R05"), catalog)
    assert dx.code == "R05" and "no reviewer text" in dx.evidence


def test_r10_closes_without_workaround(catalog):
    row = make_row(rejection_code="R10", rejection_message="Declared products fall under restricted category",
                   application_status=config.STATUS_REJECTED)
    dx = rules.diagnose(row, catalog)
    dec = rules.decide(dx, catalog)
    assert dec.fixability is Fixability.NO
    assert dec.recoverability is Recoverability.NOT_RECOVERABLE_CLOSE
    assert dec.action is RecommendedAction.CLOSE_POLITELY
    brief = rules.message_brief(dec, dx, catalog["R10"], row["step_reached"]).lower()
    assert "do not suggest any workaround" in brief
    assert catalog["R10"].standard_fix not in brief or "workaround" in brief


def test_r12_routes_to_compliance_with_neutral_wording(catalog):
    row = make_row(rejection_code="R12", rejection_message="Screening hit - refer compliance",
                   application_status=config.STATUS_REJECTED, whatsapp_allowed=True)
    dx = rules.diagnose(row, catalog)
    dec = rules.decide(dx, catalog)
    assert dec.fixability is Fixability.NEEDS_COMPLIANCE_REVIEW
    assert dec.recoverability is Recoverability.COMPLIANCE_REVIEW
    assert dec.action is RecommendedAction.COMPLIANCE_ROUTE
    brief = rules.message_brief(dec, dx, catalog["R12"], row["step_reached"])
    assert rules.COMPLIANCE_NEUTRAL_MESSAGE in brief
    for leak in ("screening", "sanction", "R12", "negative list", "hit"):
        assert leak.lower() not in rules.COMPLIANCE_NEUTRAL_MESSAGE.lower()
    # never auto-channelled to WhatsApp even when opted in
    assert rules.select_channel(True, dec.recoverability) == config.CHANNEL_MANUAL


def test_r13_inactivity_names_step_and_has_no_link(catalog):
    row = make_row(step_reached="Bank verification", days_since_last_activity=21.0)
    dx = rules.diagnose(row, catalog)
    assert (dx.code, dx.status, dx.method) == ("R13", DiagnosisStatus.INACTIVITY_INFERRED,
                                               DiagnosisMethod.INACTIVITY_RULE)
    assert "Bank verification" in dx.evidence and "21 days" in dx.evidence
    dec = rules.decide(dx, catalog)
    assert dec.recoverability is Recoverability.RECOVERABLE
    assert dec.action is RecommendedAction.REMINDER_NUDGE
    brief = rules.message_brief(dec, dx, catalog["R13"], "Bank verification")
    assert "'Bank verification' step" in brief
    assert "http" not in brief.lower() and "www" not in brief.lower()


def test_explicit_r13_code_also_reminds(catalog):
    dec = rules.decide(rules.diagnose(make_row(rejection_code="R13"), catalog), catalog)
    assert dec.action is RecommendedAction.REMINDER_NUDGE


def test_rejected_without_evidence_is_not_assumed_inactive(catalog):
    dx = rules.diagnose(make_row(application_status=config.STATUS_REJECTED), catalog)
    assert dx.code == CODE_NEEDS_HUMAN_REVIEW and dx.human_review
    dec = rules.decide(dx, catalog)
    assert dec.recoverability is Recoverability.NEEDS_HUMAN_REVIEW
    assert dec.fixability is Fixability.UNKNOWN


def test_stalled_without_step_goes_to_review(catalog):
    dx = rules.diagnose(make_row(step_reached=None), catalog)
    assert dx.code == CODE_NEEDS_HUMAN_REVIEW
    assert any("step_reached" in r for r in dx.review_reasons)


def test_unknown_status_goes_to_review(catalog):
    dx = rules.diagnose(make_row(application_status="On hold"), catalog)
    assert dx.human_review and dx.code == CODE_NEEDS_HUMAN_REVIEW
    assert rules.decide(dx, catalog).recoverability is Recoverability.NEEDS_HUMAN_REVIEW


def test_unknown_status_with_known_code_keeps_code_but_flags(catalog):
    dx = rules.diagnose(make_row(application_status="On hold", rejection_code="R01"), catalog)
    assert dx.code == "R01" and dx.human_review


def test_invalid_code_preserved_and_reviewed(catalog):
    dx = rules.diagnose(make_row(rejection_code="R99", rejection_message="Doc blurred"), catalog)
    assert dx.code == CODE_NEEDS_HUMAN_REVIEW and dx.pending_ai and dx.human_review
    assert any("R99" in r for r in dx.review_reasons)


def test_blank_code_with_text_is_not_guessed_by_rules(catalog):
    dx = rules.diagnose(make_row(rejection_message="Doc blurred and cropped, cannot verify"), catalog)
    assert dx.code == CODE_NEEDS_HUMAN_REVIEW
    assert dx.pending_ai and not dx.sensitive
    assert dx.evidence == "Doc blurred and cropped, cannot verify"


@pytest.mark.parametrize("text", [
    "Business category not supported by policy",
    "Is business category ko support nahi kar sakte",
    "Screening hit - refer compliance",
    "Possible sanctions match",
])
def test_blank_code_sensitive_text_is_suppressed(catalog, text):
    dx = rules.diagnose(make_row(rejection_message=text, application_status=config.STATUS_REJECTED), catalog)
    assert dx.sensitive and dx.human_review
    dec = rules.decide(dx, catalog)
    assert rules.message_brief(dec, dx, None, "KYC docs").startswith("No merchant message")


@pytest.mark.parametrize("text", ["Missing policy pages (T&C / refund / contact) on website",
                                  "Website pe refund policy aur privacy policy nahi hai"])
def test_policy_pages_wording_is_not_flagged_sensitive(text):
    assert not rules.is_sensitive_text(text)


@pytest.mark.parametrize("allowed,expected", [(True, config.CHANNEL_WHATSAPP), (False, config.CHANNEL_MANUAL)])
def test_whatsapp_only_with_opt_in(allowed, expected):
    assert rules.select_channel(allowed, Recoverability.RECOVERABLE) == expected
    assert rules.select_channel(allowed, Recoverability.NOT_RECOVERABLE_CLOSE) == expected


def test_human_review_cases_get_no_channel():
    assert rules.select_channel(True, Recoverability.NEEDS_HUMAN_REVIEW) == config.CHANNEL_NOT_APPLICABLE


@pytest.mark.parametrize("lang", config.SUPPORTED_LANGUAGES)
def test_supported_languages_kept(lang):
    assert rules.language_for(lang) == (lang, rules.LanguageStatus.OK)


@pytest.mark.parametrize("lang", [None, "Bengali"])
def test_unsupported_language_flagged_not_silently_english(lang):
    label, status = rules.language_for(lang)
    assert status is rules.LanguageStatus.NEEDS_REVIEW and "fallback" in label


def test_activated_is_out_of_scope():
    assert not rules.is_in_scope(config.STATUS_ACTIVATED)
    assert rules.is_in_scope(config.STATUS_STALLED) and rules.is_in_scope(config.STATUS_REJECTED)
    assert rules.is_in_scope(None) and rules.is_in_scope("On hold")
