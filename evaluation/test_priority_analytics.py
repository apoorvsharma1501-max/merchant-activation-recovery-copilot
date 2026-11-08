"""Phase 4: prioritisation heuristic, sensitivity and cause analytics."""
import math

import pandas as pd
import pytest

import config
from core import analytics, prioritization
from core.output_builder import build_results


def _frame(rows):
    base = {"recoverability": "RECOVERABLE", "expected_monthly_tpv_inr_lakh": 10.0,
            "days_since_last_activity": 10.0}
    return pd.DataFrame([{**base, "application_id": f"X{i}", **r} for i, r in enumerate(rows)])


def test_formula_and_weights_come_from_config():
    df = prioritization.score(_frame([
        {"expected_monthly_tpv_inr_lakh": 50.0, "days_since_last_activity": 0.0},
        {"expected_monthly_tpv_inr_lakh": 1.0, "days_since_last_activity": 40.0},
    ]))
    top, low = df.iloc[0], df.iloc[1]
    assert top["tpv_percentile"] == 100 and low["tpv_percentile"] == 0
    assert top["recency_score"] == 100 and low["recency_score"] == 60
    assert top["priority_score"] == pytest.approx(config.PRIORITY_WEIGHT_TPV * 100 + config.PRIORITY_WEIGHT_RECENCY * 100)
    assert low["priority_score"] == pytest.approx(config.PRIORITY_WEIGHT_RECENCY * 60)
    assert top["priority_rank"] == 1


def test_recency_score_never_negative():
    df = prioritization.score(_frame([{"days_since_last_activity": 250.0}, {}]))
    assert df["recency_score"].min() == 0


def test_only_recoverable_rows_are_ranked():
    df = prioritization.score(_frame([{}, {"recoverability": "NOT_RECOVERABLE_CLOSE"},
                                      {"recoverability": "COMPLIANCE_REVIEW"},
                                      {"recoverability": "NEEDS_HUMAN_REVIEW"}]))
    assert list(df["priority_tier"]) == ["HIGH", "UNRANKED_REVIEW", "UNRANKED_REVIEW", "UNRANKED_REVIEW"]
    assert df.loc[1:, "priority_score"].isna().all()
    assert (df.loc[1:, "priority_status"] == "NOT_APPLICABLE").all()


def test_missing_data_is_flagged_not_filled():
    df = prioritization.score(_frame([{"expected_monthly_tpv_inr_lakh": None}, {"days_since_last_activity": "x"}, {}]))
    assert list(df["priority_status"]) == ["NEEDS_DATA_REVIEW", "NEEDS_DATA_REVIEW", "OK"]
    assert df.loc[:1, "priority_score"].isna().all()
    assert df.loc[:1, "priority_tier"].eq("UNRANKED_REVIEW").all()


def test_tiers_are_quartile_based():
    df = prioritization.score(_frame([{"expected_monthly_tpv_inr_lakh": float(i)} for i in range(20)]))
    counts = df["priority_tier"].value_counts()
    assert counts["HIGH"] == 5 and counts["LOW"] == 5 and counts["MEDIUM"] == 10
    assert df.loc[df["priority_tier"] == "HIGH", "expected_monthly_tpv_inr_lakh"].min() > \
        df.loc[df["priority_tier"] == "LOW", "expected_monthly_tpv_inr_lakh"].max()


@pytest.fixture(scope="module")
def results(real_data):
    return build_results(real_data, None, run_timestamp="TEST")[0]


def test_real_ranking_covers_all_recoverable(results):
    rec = results[results["recoverability"] == "RECOVERABLE"]
    assert rec["priority_status"].eq("OK").all()
    ranks = sorted(rec["priority_rank"].astype(int))
    assert ranks == list(range(1, len(rec) + 1))
    n = len(rec)
    assert (rec["priority_tier"] == "HIGH").sum() == math.ceil(n * 0.25)


def test_sensitivity_includes_required_views(results):
    sens = prioritization.sensitivity(results)
    labels = " | ".join(sens["variant"])
    assert "TPV only" in labels and "Recency only" in labels and "BASE" in labels
    base = sens[sens["variant"].str.startswith("BASE")].iloc[0]
    assert base["top10_overlap_with_base"] == 10 and base["rank_correlation_with_base"] == 1.0


def test_cause_table_counts_and_tpv_add_up(results, real_data):
    causes = analytics.cause_table(results, real_data)
    assert causes["applications"].sum() == len(results)
    tpv = pd.to_numeric(results["expected_monthly_tpv_inr_lakh"]).sum()
    assert causes["expected_monthly_tpv_represented_lakh"].sum() == pytest.approx(tpv, abs=0.5)


def test_unresolved_never_counted_as_a_catalog_cause(results, real_data):
    causes = analytics.cause_table(results, real_data)
    unresolved = causes[causes["cause_code"].isin(["UNKNOWN", "NEEDS_HUMAN_REVIEW"])]
    assert (~unresolved["is_catalog_cause"]).all()
    top = analytics.top_causes(causes, "applications", n=20)
    assert not top["cause_code"].isin(["UNKNOWN", "NEEDS_HUMAN_REVIEW"]).any()


def test_executive_summary_matches_results(results, real_data):
    causes = analytics.cause_table(results, real_data)
    s = analytics.executive_summary(real_data, results, causes)
    assert s["activated"] + s["non_activated_processed"] == s["total_applications"]
    rec = results[results["recoverability"] == "RECOVERABLE"]
    assert s["expected_monthly_tpv_at_stake_lakh"] == pytest.approx(
        pd.to_numeric(rec["expected_monthly_tpv_inr_lakh"]).sum(), abs=0.05)
    assert len(s["top3_causes_by_count"]) == 3 and len(s["top3_causes_by_tpv"]) == 3
    assert not any(c.startswith(config.INACTIVITY_CODE) for c in s["top3_fixable_rejections_by_count"])
    assert sum(s["applications_by_tier"].values()) == s["recoverable"]


def test_abandonment_by_step_only_r13(results):
    steps = analytics.abandonment_by_step(results)
    assert steps["applications"].sum() == (results["diagnosed_reason_code"] == config.INACTIVITY_CODE).sum()
