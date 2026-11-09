"""Regression tests for the P1 fixes from the QA audit (evaluation/results/QA_audit_report.md)."""
import pandas as pd
import pytest

import config
from core import ai_diagnosis, nudge_generator, nudge_safety, prioritization, rules
from core.data_loader import load_workbook
from core.llm_client import CachedLLM
from evaluation.fake_llm import FakeLLM, cached, diag
from evaluation.test_data import make_row, write_workbook
from schemas.labels import DiagnosisStatus, Recoverability, RecommendedAction


# --- #5 (audit C04): AI-uncertain fixable diagnosis is not recoverable -----------

def test_ai_uncertain_fixable_case_goes_to_human_review(catalog, tmp_path):
    row = make_row(rejection_message="Doc blurred, or maybe the wrong file")
    llm = cached(FakeLLM(lambda s, u, sc: diag("R05", "Doc blurred", review=True)), tmp_path)
    dx = ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, llm)
    dec = rules.decide(dx, catalog)
    assert dx.code == "R05"  # suggestion kept for the reviewer
    assert dec.recoverability is Recoverability.NEEDS_HUMAN_REVIEW
    assert dec.action is RecommendedAction.HUMAN_REVIEW and dec.human_review
    assert nudge_generator.should_withhold(dx, dec)
    ranked = prioritization.score(pd.DataFrame([{"application_id": "X", "recoverability": dec.recoverability.value,
                                                 "expected_monthly_tpv_inr_lakh": 50.0,
                                                 "days_since_last_activity": 2.0}]))
    assert ranked.iloc[0]["priority_tier"] == "UNRANKED_REVIEW"


def test_confident_ai_fixable_case_stays_recoverable(catalog, tmp_path):
    row = make_row(rejection_message="Doc blurred")
    llm = cached(FakeLLM(lambda s, u, sc: diag("R05", "Doc blurred")), tmp_path)
    dx = ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, llm)
    assert rules.decide(dx, catalog).recoverability is Recoverability.RECOVERABLE


def test_ai_r10_with_review_still_closes(catalog, tmp_path):
    """A3051 handling agreed with the student is unchanged: R10, close, flagged, no message."""
    row = make_row(rejection_message="Business category not supported by policy", application_status="Rejected")
    llm = cached(FakeLLM(lambda s, u, sc: diag("R10", "Business category not supported", sensitive=True)), tmp_path)
    dx = ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, llm)
    dec = rules.decide(dx, catalog)
    assert dec.recoverability is Recoverability.NOT_RECOVERABLE_CLOSE and dec.human_review


# --- #6: wider keyword backstop ----------------------------------------------------

@pytest.mark.parametrize("text", [
    "Website offers real-money betting on cricket matches", "Possible match on OFAC list",
    "PEP match - escalate", "Adverse media hit on the director", "Name flagged by risk team, put on hold",
    "Entity linked to a high-risk jurisdiction", "Refer to L2 risk, do not process further",
])
def test_backstop_catches_stress_test_euphemisms(text):
    assert rules.is_sensitive_text(text)


@pytest.mark.parametrize("text", [
    "Doc blurred and cropped, cannot verify", "PAN ka naam aur application ka naam match nahi kar raha",
    "Signatory ka ID proof upload nahi hua", "Missing policy pages (T&C / refund / contact) on website",
    "Website pe refund policy aur privacy policy nahi hai", "Alphabet letters mismatch",
])
def test_backstop_still_quiet_on_ordinary_notes(text):
    assert not rules.is_sensitive_text(text)


# --- #8: inactivity longer than account age is flagged, not altered ---------------

def test_inactivity_exceeding_account_age_is_flagged(tmp_path):
    apps = pd.read_excel(config.DEFAULT_WORKBOOK, sheet_name=config.APPLICATIONS_SHEET,
                         dtype=object).dropna(how="all").reset_index(drop=True)
    apps.loc[0, "signup_date"] = "25 Sep 2026"         # 5 days before snapshot
    apps.loc[0, "days_since_last_activity"] = 12        # impossible
    apps.loc[1, "signup_date"] = "not a date"
    data = load_workbook(write_workbook(tmp_path, apps=apps))
    clean = data.applications
    assert "exceeds days since signup (5 d)" in clean.loc[0, "activity_consistency_flag"]
    assert clean.loc[0, "days_since_last_activity"] == 12  # value untouched
    assert clean.loc[1, "activity_consistency_flag"] == "signup_date unparseable"
    assert all(i.severity == "WARNING" for i in data.issues)


def test_real_workbook_has_21_inconsistent_rows(real_data):
    assert real_data.applications["activity_consistency_flag"].notna().sum() == 21


# --- #9: messages may not add content beyond the brief ----------------------------

@pytest.mark.parametrize("back", [
    "Please sign in and continue. There is nothing to worry about.",
    "Please sign in and continue. We are here if you need help.",
    "Please sign in and continue. Thank you for choosing to grow your business with us!",
    "Please sign in and continue. Feel free to contact us.",
])
def test_safety_blocks_extra_content(back):
    issues = nudge_safety.check(back, back, "English", RecommendedAction.REMINDER_NUDGE,
                                "Ask them to sign in and continue from the 'KYC docs' step.", "KYC docs")
    assert any("adds content not in the brief" in i for i in issues), issues


def test_plain_reminder_with_thanks_passes():
    msg = "Hello! Your onboarding is paused at the 'KYC docs' step. Please sign in and continue from there. Thank you!"
    assert nudge_safety.check(msg, msg, "English", RecommendedAction.REMINDER_NUDGE,
                              "continue from the 'KYC docs' step", "KYC docs") == []


def test_closure_thanking_for_choosing_us_is_allowed():
    msg = "We are unable to support this business category, so the application is closed. Thank you for choosing us."
    assert nudge_safety.check(msg, msg, "English", RecommendedAction.CLOSE_POLITELY, "closure") == []


# --- #10: code/text contradiction on coded rows ------------------------------------

def _coded(catalog, tmp_path, code, text, answer):
    row = make_row(rejection_code=code, rejection_message=text)
    llm = cached(FakeLLM(lambda s, u, sc: answer), tmp_path)
    return ai_diagnosis.check_consistency(row, rules.diagnose(row, catalog), catalog, llm), llm


def test_contradiction_keeps_code_but_goes_to_review(catalog, tmp_path):
    dx, _ = _coded(catalog, tmp_path, "R01", "Bank account holder name does not match",
                   diag("R03", "Bank account holder name does not match"))
    assert dx.code == "R01" and dx.status is DiagnosisStatus.NEEDS_HUMAN_REVIEW and dx.human_review
    assert any("suggests R03" in r for r in dx.review_reasons)
    dec = rules.decide(dx, catalog)
    assert dec.recoverability is Recoverability.NEEDS_HUMAN_REVIEW
    assert nudge_generator.should_withhold(dx, dec)


def test_agreement_leaves_rule_diagnosis_untouched(catalog, tmp_path):
    dx, _ = _coded(catalog, tmp_path, "R01", "PAN name mismatch", diag("R01", "PAN name mismatch"))
    assert dx.status is DiagnosisStatus.KNOWN_CODE and not dx.human_review and dx.model == "RULE_ONLY"


def test_unknown_from_ai_does_not_flag(catalog, tmp_path):
    dx, _ = _coded(catalog, tmp_path, "R12", "Compliance review pending", diag("UNKNOWN", ""))
    assert dx.status is DiagnosisStatus.KNOWN_CODE and not dx.human_review


def test_ai_unavailable_does_not_flag(catalog, tmp_path):
    row = make_row(rejection_code="R01", rejection_message="Bank name differs")
    off = CachedLLM(inner=None, mode="cache", cache_path=tmp_path / "none.json")
    dx = ai_diagnosis.check_consistency(row, rules.diagnose(row, catalog), catalog, off)
    assert dx.status is DiagnosisStatus.KNOWN_CODE and not dx.human_review


# --- #7 (documentation): effective weighting is reported -----------------------------

def test_effective_tpv_share_reported(real_data):
    from core.output_builder import build_results
    res, _ = build_results(real_data, None, run_timestamp="TEST")
    share = prioritization.effective_tpv_share(res)
    assert share is not None and 0.5 < share < 1.0
