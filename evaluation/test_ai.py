"""AI diagnosis, nudge drafting, safety checks and cache - all with a fake model."""
import pytest

import config
from core import ai_diagnosis, nudge_generator, nudge_safety, rules
from core.llm_client import CachedLLM, LLMResult
from core.output_builder import build_results, coverage_summary
from evaluation.fake_llm import FakeLLM, cached, diag, nudge
from evaluation.test_data import make_row
from schemas.labels import (
    CODE_UNKNOWN, DiagnosisMethod, DiagnosisStatus, NudgeStatus, Recoverability, RecommendedAction,
)


def _classify(catalog, tmp_path, text, responder, status=config.STATUS_STALLED, code=None):
    row = make_row(rejection_message=text, application_status=status, rejection_code=code)
    rule_dx = rules.diagnose(row, catalog)
    llm = cached(FakeLLM(responder), tmp_path)
    return ai_diagnosis.classify(row, rule_dx, catalog, llm), llm


# --- Diagnosis -------------------------------------------------------------

def test_clear_english_text_is_classified_with_evidence(catalog, tmp_path):
    text = "Doc blurred and cropped, cannot verify"
    dx, _ = _classify(catalog, tmp_path, text, lambda s, u, sc: diag("R05", "Doc blurred and cropped"))
    assert (dx.code, dx.status, dx.method) == ("R05", DiagnosisStatus.AI_CLASSIFIED,
                                               DiagnosisMethod.LLM_TEXT_CLASSIFICATION)
    assert not dx.human_review and dx.model == "fake-model"
    dec = rules.decide(dx, catalog)
    assert dec.recoverability is Recoverability.RECOVERABLE


def test_hinglish_text_is_classified(catalog, tmp_path):
    text = "PAN ka naam aur application ka naam match nahi kar raha"
    dx, _ = _classify(catalog, tmp_path, text, lambda s, u, sc: diag("R01", "PAN ka naam aur application ka naam"))
    assert dx.code == "R01" and dx.status is DiagnosisStatus.AI_CLASSIFIED


def test_ambiguous_text_returns_unknown_and_review(catalog, tmp_path):
    dx, _ = _classify(catalog, tmp_path, "Please check again", lambda s, u, sc: diag("UNKNOWN", ""))
    assert dx.code == CODE_UNKNOWN and dx.human_review
    assert rules.decide(dx, catalog).recoverability is Recoverability.NEEDS_HUMAN_REVIEW


def test_restricted_category_text_becomes_r10_close_with_review_and_no_message(catalog, tmp_path):
    """Agreed handling for A3051: R10, closed, flagged for human review, no message until confirmed."""
    text = "Business category not supported by policy"
    dx, llm = _classify(catalog, tmp_path, text,
                        lambda s, u, sc: diag("R10", "Business category not supported", sensitive=True),
                        status=config.STATUS_REJECTED)
    assert dx.code == "R10" and dx.sensitive and dx.human_review
    dec = rules.decide(dx, catalog)
    assert dec.recoverability is Recoverability.NOT_RECOVERABLE_CLOSE and dec.human_review
    n = nudge_generator.generate(make_row(application_status=config.STATUS_REJECTED), dx, dec, catalog["R10"], llm)
    assert n.status is NudgeStatus.NO_NUDGE_HUMAN_REVIEW and n.text is None


def test_compliance_text_suggesting_r12_is_withheld(catalog, tmp_path):
    text = "Screening hit - refer compliance"
    dx, llm = _classify(catalog, tmp_path, text, lambda s, u, sc: diag("R12", "Screening hit", sensitive=True),
                        status=config.STATUS_REJECTED)
    dec = rules.decide(dx, catalog)
    assert dec.recoverability is Recoverability.COMPLIANCE_REVIEW
    n = nudge_generator.generate(make_row(), dx, dec, catalog["R12"], llm)
    assert n.status is NudgeStatus.NO_NUDGE_HUMAN_REVIEW


def test_keyword_guard_overrides_model_saying_not_sensitive(catalog, tmp_path):
    text = "Possible sanctions match, doc also blurred"
    dx, _ = _classify(catalog, tmp_path, text, lambda s, u, sc: diag("R05", "doc also blurred"))
    assert dx.sensitive and dx.human_review
    assert rules.decide(dx, catalog).recoverability is Recoverability.NEEDS_HUMAN_REVIEW


def test_invalid_json_twice_goes_to_human_review(catalog, tmp_path):
    dx, llm = _classify(catalog, tmp_path, "Doc blurred", lambda s, u, sc: None)
    assert dx.status is DiagnosisStatus.NEEDS_HUMAN_REVIEW
    assert any("AI diagnosis rejected" in r for r in dx.review_reasons)
    assert llm.calls == 2  # exactly one retry


def test_invalid_then_valid_json_recovers_on_retry(catalog, tmp_path):
    answers = iter([None, diag("R05", "Doc blurred")])
    dx, llm = _classify(catalog, tmp_path, "Doc blurred", lambda s, u, sc: next(answers))
    assert dx.code == "R05" and llm.calls == 2
    assert "previous answer was rejected" in llm.inner.prompts[1]


def test_non_catalog_code_is_rejected(catalog, tmp_path):
    dx, _ = _classify(catalog, tmp_path, "Doc blurred", lambda s, u, sc: diag("R99", "Doc blurred"))
    assert dx.status is DiagnosisStatus.NEEDS_HUMAN_REVIEW


def test_invented_evidence_quote_is_rejected(catalog, tmp_path):
    dx, _ = _classify(catalog, tmp_path, "Doc blurred", lambda s, u, sc: diag("R05", "image is low resolution"))
    assert dx.status is DiagnosisStatus.NEEDS_HUMAN_REVIEW
    assert any("not an exact substring" in r for r in dx.review_reasons)


def test_refusal_goes_to_human_review_without_retry(catalog, tmp_path):
    dx, llm = _classify(catalog, tmp_path, "Doc blurred",
                        lambda s, u, sc: LLMResult(None, "refusal", "fake-model", "declined"))
    assert dx.status is DiagnosisStatus.NEEDS_HUMAN_REVIEW and llm.calls == 1


def test_invalid_original_code_keeps_suggestion_but_flags(catalog, tmp_path):
    dx, _ = _classify(catalog, tmp_path, "Doc blurred", lambda s, u, sc: diag("R05", "Doc blurred"), code="R99")
    assert dx.code == "R05" and dx.human_review
    n = nudge_generator.generate(make_row(), dx, rules.decide(dx, catalog), catalog["R05"], None)
    assert n.status is NudgeStatus.NO_NUDGE_HUMAN_REVIEW


def test_only_reviewer_text_and_catalog_are_sent(catalog, tmp_path):
    row = make_row(rejection_message="Doc blurred", application_id="A9999", city="Pune", industry="Electronics")
    fake = FakeLLM(lambda s, u, sc: diag("R05", "Doc blurred"))
    ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, cached(fake, tmp_path))
    prompt = fake.prompts[0]
    for private in ("A9999", "Pune", "Electronics"):
        assert private not in prompt


# --- Safety checks ----------------------------------------------------------

BRIEF = "Language: English\nWhat to do (approved wording): Re-upload a clear scan under 5 MB."


@pytest.mark.parametrize("text,expected", [
    ("Please visit https://example.com to continue.", "link"),
    ("Upload it at www.example.in please.", "link"),
    ("Call us on 98765 43210.", "phone"),
    ("Your account will be activated within 2 days.", "numbers not in the brief"),
    ("Your account will be activated soon.", "promise"),
    ("This is about code R05.", "internal rejection code"),
])
def test_safety_catches_unsafe_english(text, expected):
    issues = nudge_safety.check(text, text, "English", RecommendedAction.CORRECTIVE_NUDGE, BRIEF, "KYC docs")
    assert any(expected in i for i in issues), issues


def test_safety_allows_numbers_from_brief():
    text = "Please re-upload a clear scan under 5 MB, then sign in and resubmit."
    assert nudge_safety.check(text, text, "English", RecommendedAction.CORRECTIVE_NUDGE, BRIEF) == []


def test_safety_blocks_r10_workaround():
    back = "We cannot support this category. You could choose a different category and reapply."
    issues = nudge_safety.check(back, back, "English", RecommendedAction.CLOSE_POLITELY, "closure")
    assert any("workaround" in i for i in issues)


def test_safety_blocks_compliance_disclosure():
    back = "Your application matched a sanctions screening list."
    issues = nudge_safety.check(back, back, "English", RecommendedAction.COMPLIANCE_ROUTE, "neutral")
    assert any("compliance disclosure" in i for i in issues)


def test_neutral_compliance_text_passes():
    msg = rules.COMPLIANCE_NEUTRAL_MESSAGE
    assert nudge_safety.check(msg, msg, "English", RecommendedAction.COMPLIANCE_ROUTE, msg) == []


@pytest.mark.parametrize("language,text,ok", [
    ("Tamil", "உங்கள் KYC ஆவணங்களை மீண்டும் பதிவேற்றவும்.", True),
    ("Tamil", "Please upload your KYC documents again.", False),
    ("Hindi", "कृपया अपने KYC दस्तावेज़ फिर से अपलोड करें।", True),
    ("Kannada", "ದಯವಿಟ್ಟು ನಿಮ್ಮ KYC ದಾಖಲೆಗಳನ್ನು ಮತ್ತೆ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.", True),
    ("Hinglish", "कृपया KYC documents dobara upload karein.", False),
    ("Hinglish", "Kripya apne KYC documents dobara upload karein.", True),
])
def test_script_check(language, text, ok):
    back = "Please upload your KYC documents again."
    issues = nudge_safety.check(text, back, language, RecommendedAction.CORRECTIVE_NUDGE, "brief")
    assert (not any("script" in i for i in issues)) == ok, issues


def test_reminder_must_name_step():
    back = "Please sign in and continue your onboarding."
    issues = nudge_safety.check(back, back, "English", RecommendedAction.REMINDER_NUDGE, "b", "Bank verification")
    assert any("does not name the step" in i for i in issues)


# --- Nudge generation ------------------------------------------------------

def _known(catalog, code, **row_kw):
    row = make_row(rejection_code=code, **row_kw)
    dx = rules.diagnose(row, catalog)
    return row, dx, rules.decide(dx, catalog)


def test_tamil_nudge_drafted_and_brief_uses_catalog_fix(catalog, tmp_path):
    row, dx, dec = _known(catalog, "R02", preferred_language="Tamil")
    fake = FakeLLM(lambda s, u, sc: nudge("உங்கள் GSTIN சரியாக உள்ளிடவும். பின்னர் உள்நுழைந்து மீண்டும் சமர்ப்பிக்கவும்.",
                                         "Enter your GSTIN correctly. Then sign in and resubmit."))
    n = nudge_generator.generate(row, dx, dec, catalog["R02"], cached(fake, tmp_path))
    assert n.status is NudgeStatus.DRAFTED and n.safety_passed
    assert catalog["R02"].standard_fix in fake.prompts[0]
    assert "Language: Tamil" in fake.prompts[0]


def test_unsafe_draft_is_retried_then_marked(catalog, tmp_path):
    row, dx, dec = _known(catalog, "R05")
    bad = nudge("Re-upload now; you will be activated within 2 days.")
    fake = FakeLLM(lambda s, u, sc: bad)
    llm = cached(fake, tmp_path)
    n = nudge_generator.generate(row, dx, dec, catalog["R05"], llm)
    assert llm.calls == 2 and "rejected by automatic checks" in fake.prompts[1]
    assert n.status is NudgeStatus.NO_NUDGE_HUMAN_REVIEW and n.safety_passed is False
    assert n.text  # kept so a reviewer can see what was wrong


def test_unsafe_then_safe_draft_passes(catalog, tmp_path):
    row, dx, dec = _known(catalog, "R05")
    answers = iter([nudge("Done within 2 days."),
                    nudge("Please re-upload a clear, full-page colour scan under 5 MB, then sign in and resubmit.")])
    n = nudge_generator.generate(row, dx, dec, catalog["R05"], cached(FakeLLM(lambda s, u, sc: next(answers)), tmp_path))
    assert n.status is NudgeStatus.DRAFTED and n.safety_passed


def test_english_compliance_uses_fixed_text_without_model(catalog, tmp_path):
    row, dx, dec = _known(catalog, "R12", application_status=config.STATUS_REJECTED)
    fake = FakeLLM(lambda s, u, sc: pytest.fail("model must not be called"))
    n = nudge_generator.generate(row, dx, dec, catalog["R12"], cached(fake, tmp_path))
    assert n.text == rules.COMPLIANCE_NEUTRAL_MESSAGE and n.status is NudgeStatus.NEUTRAL_COMPLIANCE


def test_no_ai_english_template_and_tamil_not_generated(catalog):
    row, dx, dec = _known(catalog, "R03")
    n = nudge_generator.generate(row, dx, dec, catalog["R03"], None)
    assert n.status is NudgeStatus.DRAFTED and catalog["R03"].standard_fix in n.text
    row_t, dx_t, dec_t = _known(catalog, "R03", preferred_language="Tamil")
    n_t = nudge_generator.generate(row_t, dx_t, dec_t, catalog["R03"], None)
    assert n_t.status is NudgeStatus.NOT_GENERATED and n_t.text is None


@pytest.mark.parametrize("code", [f"R{i:02d}" for i in range(1, 14) if i not in (10, 12)] + ["R10"])
def test_english_templates_pass_safety_for_every_code(catalog, code):
    row, dx, dec = _known(catalog, code)
    n = nudge_generator.generate(row, dx, dec, catalog[code], None)
    assert n.safety_passed, (code, n.issues)


# --- Cache -------------------------------------------------------------------

def test_cache_makes_second_run_free_and_identical(catalog, tmp_path):
    fake = FakeLLM(lambda s, u, sc: diag("R05", "Doc blurred"))
    llm = cached(fake, tmp_path)
    row = make_row(rejection_message="Doc blurred")
    ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, llm)
    llm.save()
    replay = CachedLLM(inner=None, mode="cache", cache_path=tmp_path / "cache.json", model="fake-model")
    dx = ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, replay)
    assert dx.code == "R05" and replay.cache_hits == 1 and replay.calls == 0
    # a different model name must not reuse another model's answers
    other = CachedLLM(inner=None, mode="cache", cache_path=tmp_path / "cache.json", model="other-model")
    assert ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, other).code != "R05"


def test_cache_only_miss_falls_back_to_rules(catalog, tmp_path):
    replay = CachedLLM(inner=None, mode="cache", cache_path=tmp_path / "none.json")
    row = make_row(rejection_message="Doc blurred")
    dx = ai_diagnosis.classify(row, rules.diagnose(row, catalog), catalog, replay)
    assert dx.status is DiagnosisStatus.NEEDS_HUMAN_REVIEW
    assert any("AI unavailable" in r for r in dx.review_reasons)


# --- End to end with a fake model on the real workbook ------------------------

def _fake_responder(system, user, schema):
    if "Reviewer note:" in user:
        note = user.split("<<<\n", 1)[1].split("\n>>>", 1)[0]
        table = {"blurred": ("R05", "Doc blurred and cropped"),
                 "PAN ka naam": ("R01", "PAN ka naam aur application ka naam"),
                 "Signatory": ("R09", "Signatory ka ID proof"),
                 "not supported": ("R10", "Business category not supported")}
        for key, (code, quote) in table.items():
            if key in note:
                return diag(code, quote, sensitive=(code == "R10"))
        return diag("UNKNOWN", "")
    lang = user.splitlines()[0].split(": ", 1)[1]
    step = next((l.split("'")[1] for l in user.splitlines() if "stopped:" in l), "")
    samples = {"Tamil": "தயவுசெய்து உள்நுழைந்து தொடரவும்.", "Kannada": "ದಯವಿಟ್ಟು ಲಾಗಿನ್ ಮಾಡಿ ಮುಂದುವರಿಸಿ.",
               "Hindi": "कृपया साइन इन करके आगे बढ़ें।", "Marathi": "कृपया साइन इन करून पुढे जा.",
               "Hinglish": "Kripya sign in karke aage badhein.", "English": "Please sign in and continue."}
    back = f"Please sign in and continue from the {step} step." if step else "We are unable to support this category; the application is closed."
    if "fixed neutral text" in user:
        back = rules.COMPLIANCE_NEUTRAL_MESSAGE
    msg = samples[lang] if lang != "English" else back
    return nudge(msg, back)


def test_full_workbook_with_fake_ai(real_data, tmp_path):
    llm = cached(FakeLLM(_fake_responder), tmp_path)
    res, _ = build_results(real_data, llm, run_timestamp="TEST")
    s = coverage_summary(real_data, res)
    assert s["non_activated_processed"] == 75
    by_id = res.set_index("application_id")
    assert by_id.loc["A3022", "diagnosed_reason_code"] == "R05"
    assert by_id.loc["A3028", "diagnosed_reason_code"] == "R01"
    assert by_id.loc["A3081", "diagnosed_reason_code"] == "R09"
    a3051 = by_id.loc["A3051"]
    assert a3051["diagnosed_reason_code"] == "R10"
    assert a3051["recoverability"] == "NOT_RECOVERABLE_CLOSE"
    assert bool(a3051["human_review_required"]) and a3051["nudge_status"] == "NO_NUDGE_HUMAN_REVIEW"
    assert a3051["whatsapp_allowed"] and a3051["recommended_channel"] == "Not applicable"  # opted in, but withheld
    assert s["recoverable"] == 67 and s["not_recoverable_close"] == 5 and s["compliance_review"] == 3
    assert s["needs_human_review"] == 0
    assert not ((res["recommended_channel"] == "WhatsApp") & ~res["whatsapp_allowed"]).any()
    drafted = res[res["nudge_status"].isin(["DRAFTED", "NEUTRAL_COMPLIANCE"])]
    assert drafted["nudge_safety_check_passed"].all()
    withheld = res[res["nudge_status"] == "NO_NUDGE_HUMAN_REVIEW"]
    assert (withheld["recommended_channel"] == "Not applicable").all()
