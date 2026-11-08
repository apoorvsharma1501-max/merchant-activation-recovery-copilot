"""Order RECOVERABLE applications for follow-up (handover section 8).

This is a transparent operational heuristic, NOT a prediction of recovery probability:
    tpv_percentile  = percentile of expected monthly TPV among recoverable rows, 0-100
    recency_score   = max(0, 100 - days_since_last_activity)
    priority_score  = w_tpv * tpv_percentile + w_recency * recency_score   (weights in config.py)
Tiers: top 25% HIGH, middle 50% MEDIUM, bottom 25% LOW (by rank within recoverable rows).
Close, compliance and human-review rows are never ranked as outreach opportunities.
"""
from __future__ import annotations

import math

import pandas as pd

import config
from schemas.labels import Recoverability

TIER_HIGH, TIER_MEDIUM, TIER_LOW, TIER_UNRANKED = "HIGH", "MEDIUM", "LOW", "UNRANKED_REVIEW"
STATUS_OK, STATUS_NEEDS_DATA, STATUS_NOT_APPLICABLE = "OK", "NEEDS_DATA_REVIEW", "NOT_APPLICABLE"


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def percentile_0_100(values: pd.Series) -> pd.Series:
    """Rank-based percentile scaled so the lowest value is 0 and the highest is 100 (ties averaged)."""
    n = values.notna().sum()
    if n == 0:
        return values * float("nan")
    if n == 1:
        return values.where(values.isna(), 100.0)
    ranks = values.rank(method="average")
    return (ranks - 1) / (n - 1) * 100


def score(results: pd.DataFrame, w_tpv: float = config.PRIORITY_WEIGHT_TPV,
          w_recency: float = config.PRIORITY_WEIGHT_RECENCY) -> pd.DataFrame:
    """Return a copy of `results` with the priority columns filled."""
    out = results.copy()
    for col in ("tpv_percentile", "recency_score", "priority_score", "priority_rank"):
        out[col] = float("nan")
    out["priority_tier"] = TIER_UNRANKED
    out["priority_status"] = STATUS_NOT_APPLICABLE

    tpv = _num(out["expected_monthly_tpv_inr_lakh"])
    days = _num(out["days_since_last_activity"])
    recoverable = out["recoverability"] == Recoverability.RECOVERABLE.value
    valid = recoverable & tpv.notna() & days.notna() & (tpv >= 0) & (days >= 0)

    out.loc[recoverable & ~valid, "priority_status"] = STATUS_NEEDS_DATA
    out.loc[valid, "priority_status"] = STATUS_OK
    out.loc[valid, "tpv_percentile"] = percentile_0_100(tpv[valid]).round(1)
    out.loc[valid, "recency_score"] = (100 - days[valid]).clip(lower=0)
    out.loc[valid, "priority_score"] = (w_tpv * out.loc[valid, "tpv_percentile"]
                                        + w_recency * out.loc[valid, "recency_score"]).round(1)

    ranked = out[valid].assign(_tpv=tpv[valid]).sort_values(
        ["priority_score", "_tpv", "application_id"], ascending=[False, False, True])
    n = len(ranked)
    if n:
        high_cut, low_cut = math.ceil(n * 0.25), n - math.ceil(n * 0.25)
        for position, idx in enumerate(ranked.index, start=1):
            out.at[idx, "priority_rank"] = position
            out.at[idx, "priority_tier"] = (TIER_HIGH if position <= high_cut
                                            else TIER_LOW if position > low_cut else TIER_MEDIUM)
    return out


def sensitivity(results: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Compare the combined heuristic with TPV-only, recency-only and other weightings.

    For each variant: how many of the base top-N stay in its top-N, and the rank correlation
    (Spearman) with the base order. Large changes mean the order depends heavily on the weights.
    """
    base_w = config.PRIORITY_WEIGHT_TPV
    variants = [("TPV only", 1.0), ("0.9 TPV / 0.1 recency", 0.9), ("0.8 / 0.2", 0.8),
                (f"BASE {base_w:.2f} / {1 - base_w:.2f}", base_w), ("0.6 / 0.4", 0.6),
                ("0.5 / 0.5", 0.5), ("Recency only", 0.0)]
    base = score(results)
    base_ok = base[base["priority_status"] == STATUS_OK]
    base_top = set(base_ok.nsmallest(top_n, "priority_rank")["application_id"])
    rows = []
    for label, w in variants:
        s = score(results, w_tpv=w, w_recency=1 - w)
        s_ok = s[s["priority_status"] == STATUS_OK]
        top = s_ok.nsmallest(top_n, "priority_rank")
        merged = base_ok[["application_id", "priority_rank"]].merge(
            s_ok[["application_id", "priority_rank"]], on="application_id", suffixes=("_base", "_v"))
        # Columns are already ranks, so Pearson on them = Spearman rank correlation (no scipy needed).
        rho = merged["priority_rank_base"].astype(float).corr(merged["priority_rank_v"].astype(float))
        rows.append({
            "variant": label, "w_tpv": w, "w_recency": round(1 - w, 2),
            f"top{top_n}_overlap_with_base": len(base_top & set(top["application_id"])),
            "rank_correlation_with_base": round(float(rho), 3),
            f"top{top_n}_ids": ", ".join(top["application_id"]),
            f"top{top_n}_expected_tpv_lakh": round(float(_num(top["expected_monthly_tpv_inr_lakh"]).sum()), 1),
        })
    return pd.DataFrame(rows)
