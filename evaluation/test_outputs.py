"""End-to-end checks on the real workbook: coverage, safety gates, schema."""
import pandas as pd
import pytest

import config
from core.output_builder import OUTPUT_COLUMNS, build_results, coverage_summary


@pytest.fixture(scope="module")
def results(real_data):
    res, audit = build_results(real_data, run_timestamp="TEST")
    return res, audit


def test_one_row_per_non_activated_application(real_data, results):
    res, audit = results
    apps = real_data.applications
    expected = set(apps.loc[apps["application_status"] != config.STATUS_ACTIVATED, "application_id"])
    assert len(res) == len(expected) == res["application_id"].nunique()
    assert set(res["application_id"]) == expected


def test_activated_get_no_nudge(real_data, results):
    res, audit = results
    activated = set(real_data.applications.query("application_status == 'Activated'")["application_id"])
    assert not activated & set(res["application_id"])
    assert set(audit["application_id"]) == activated


def test_schema_columns(results):
    assert list(results[0].columns) == OUTPUT_COLUMNS


def test_whatsapp_never_recommended_without_opt_in(results):
    res = results[0]
    assert not ((res["recommended_channel"] == config.CHANNEL_WHATSAPP) & ~res["whatsapp_allowed"]).any()


def test_source_fields_unmodified(real_data, results):
    res = results[0].set_index("application_id")
    raw = real_data.applications_raw.set_index("application_id")
    for app_id in res.index:
        a, b = res.loc[app_id, "rejection_message_original"], raw.loc[app_id, "rejection_message"]
        assert (pd.isna(a) and pd.isna(b)) or a == b


def test_r12_rows_never_expose_reason_in_brief(results):
    res = results[0]
    r12 = res[res["diagnosed_reason_code"] == "R12"]
    assert len(r12) > 0
    for brief in r12["nudge_brief"]:
        assert "screening" not in brief.lower() and "sanction" not in brief.lower()
    assert (r12["recommended_channel"] == config.CHANNEL_MANUAL).all()


def test_blank_code_text_rows_are_held_for_review(results):
    res = results[0]
    held = res[res["rejection_code_original"].isna() & res["rejection_message_original"].notna()]
    assert set(held["application_id"]) == {"A3022", "A3028", "A3051", "A3081"}
    assert (held["recoverability"] == "NEEDS_HUMAN_REVIEW").all()
    assert (held["nudge_status"] == "NO_NUDGE_HUMAN_REVIEW").all()
    a3051 = held.set_index("application_id").loc["A3051"]
    assert "withheld" in a3051["diagnosed_reason"]


def test_rule_only_mode_drafts_english_templates_only(results):
    res = results[0]
    assert res["nudge_review_required"].all()
    drafted = res[res["nudge_text"].notna()]
    assert set(drafted["preferred_language"]) <= {"English"}
    assert drafted["nudge_safety_check_passed"].all()
    assert (drafted["nudge_model"] == "RULE_TEMPLATE").all()
    other = res[(res["preferred_language"] != "English") & (res["nudge_status"] != "NO_NUDGE_HUMAN_REVIEW")]
    assert (other["nudge_status"] == "NOT_GENERATED").all()


def test_summary_counts_add_up(real_data, results):
    s = coverage_summary(real_data, results[0])
    assert s["activated"] + s["non_activated_processed"] == s["total_applications"]
    assert (s["recoverable"] + s["not_recoverable_close"] + s["compliance_review"]
            + s["needs_human_review"]) == s["non_activated_processed"]
