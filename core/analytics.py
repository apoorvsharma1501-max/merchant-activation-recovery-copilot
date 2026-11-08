"""Systemic-cause analysis and executive summary (handover section 9).

Every number is computed from the results table at runtime. "Expected monthly TPV" is
the merchant's declared expectation at signup - it is TPV represented by these
applications, not TPV recovered, revenue, or a forecast.
"""
from __future__ import annotations

import pandas as pd

import config
from core.data_loader import LoadedData
from schemas.labels import CODE_NEEDS_HUMAN_REVIEW, CODE_UNKNOWN, Recoverability

UNRESOLVED = {CODE_UNKNOWN, CODE_NEEDS_HUMAN_REVIEW}


def _tpv(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["expected_monthly_tpv_inr_lakh"], errors="coerce")


def cause_table(results: pd.DataFrame, data: LoadedData) -> pd.DataFrame:
    """One row per diagnosed cause among non-activated applications.
    UNKNOWN / NEEDS_HUMAN_REVIEW stay as their own rows and are never merged into a catalog cause."""
    df = results.assign(_tpv=_tpv(results))
    total = len(df)
    rows = []
    for code, g in df.groupby("diagnosed_reason_code"):
        entry = data.catalog.get(code)
        rows.append({
            "cause_code": code,
            "cause": entry.reviewer_reason if entry else "Unresolved - human review",
            "is_catalog_cause": code not in UNRESOLVED,
            "fixability": entry.fixability.value if entry else "Unknown",
            "applications": len(g),
            "share_of_non_activated_pct": round(100 * len(g) / total, 1) if total else 0.0,
            "recoverable": int((g["recoverability"] == Recoverability.RECOVERABLE.value).sum()),
            "recoverability_outcomes": "; ".join(f"{k}: {v}" for k, v in g["recoverability"].value_counts().items()),
            "expected_monthly_tpv_represented_lakh": round(float(g["_tpv"].sum()), 1),
            "via_ai_classification": int((g["diagnosis_method"] == "LLM_TEXT_CLASSIFICATION").sum()),
        })
    table = pd.DataFrame(rows)
    return table.sort_values(["applications", "expected_monthly_tpv_represented_lakh"],
                             ascending=False).reset_index(drop=True)


def top_causes(table: pd.DataFrame, by: str, n: int = 3, fixable_only: bool = False,
               exclude: set[str] | None = None) -> pd.DataFrame:
    t = table[table["is_catalog_cause"]]
    if fixable_only:
        t = t[t["fixability"] == "Yes"]
    if exclude:
        t = t[~t["cause_code"].isin(exclude)]
    tiebreak = "expected_monthly_tpv_represented_lakh" if by == "applications" else "applications"
    return t.sort_values([by, tiebreak, "cause_code"], ascending=[False, False, True]).head(n)


def abandonment_by_step(results: pd.DataFrame) -> pd.DataFrame:
    """Where merchants with no rejection (R13) stopped - a product-funnel view."""
    g = results[results["diagnosed_reason_code"] == config.INACTIVITY_CODE].assign(_tpv=_tpv(results))
    out = g.groupby("step_reached").agg(applications=("application_id", "count"),
                                        expected_monthly_tpv_represented_lakh=("_tpv", "sum"))
    out["expected_monthly_tpv_represented_lakh"] = out["expected_monthly_tpv_represented_lakh"].round(1)
    return out.sort_values("applications", ascending=False).reset_index()


def executive_summary(data: LoadedData, results: pd.DataFrame, causes: pd.DataFrame) -> dict:
    apps = data.applications
    rec = results["recoverability"].value_counts()
    recov = results[results["recoverability"] == Recoverability.RECOVERABLE.value]
    tiers = recov.assign(_tpv=_tpv(recov)).groupby("priority_tier")["_tpv"].agg(["count", "sum"])

    def fmt(t: pd.DataFrame, col: str) -> list[str]:
        unit = " lakh" if col.startswith("expected") else ""
        return [f"{r.cause_code} {r.cause} ({getattr(r, col)}{unit})" for r in t.itertuples()]

    return {
        "total_applications": len(apps),
        "activated": int((apps["application_status"] == config.STATUS_ACTIVATED).sum()),
        "stalled": int((apps["application_status"] == config.STATUS_STALLED).sum()),
        "rejected": int((apps["application_status"] == config.STATUS_REJECTED).sum()),
        "non_activated_processed": len(results),
        "fixable_per_catalog": int((results["fixability"] == "Yes").sum()),
        "recoverable": int(rec.get(Recoverability.RECOVERABLE.value, 0)),
        "not_recoverable_close": int(rec.get(Recoverability.NOT_RECOVERABLE_CLOSE.value, 0)),
        "compliance_review": int(rec.get(Recoverability.COMPLIANCE_REVIEW.value, 0)),
        "needs_human_review": int(rec.get(Recoverability.NEEDS_HUMAN_REVIEW.value, 0)),
        "human_review_flagged": int(results["human_review_required"].sum()),
        "expected_monthly_tpv_at_stake_lakh": round(float(_tpv(recov).sum()), 1),
        "tpv_at_stake_by_tier_lakh": {k: round(float(v), 1) for k, v in tiers["sum"].items()},
        "applications_by_tier": {k: int(v) for k, v in tiers["count"].items()},
        "top3_causes_by_count": fmt(top_causes(causes, "applications"), "applications"),
        "top3_causes_by_tpv": fmt(top_causes(causes, "expected_monthly_tpv_represented_lakh"),
                                  "expected_monthly_tpv_represented_lakh"),
        "top3_fixable_rejections_by_count": fmt(
            top_causes(causes, "applications", fixable_only=True, exclude={config.INACTIVITY_CODE}),
            "applications"),
        "top3_fixable_rejections_by_tpv": fmt(
            top_causes(causes, "expected_monthly_tpv_represented_lakh", fixable_only=True,
                       exclude={config.INACTIVITY_CODE}),
            "expected_monthly_tpv_represented_lakh"),
    }


def summary_markdown(s: dict, causes: pd.DataFrame, steps: pd.DataFrame, sens: pd.DataFrame,
                     results: pd.DataFrame) -> str:
    def bullets(items):
        return "\n".join(f"{i}. {x}" for i, x in enumerate(items, 1))

    top = results[results["priority_tier"] == "HIGH"].sort_values("priority_rank")
    lines = [
        "# Executive summary - onboarding recovery",
        "",
        "All figures computed from the workbook at runtime. *Expected monthly TPV* is what merchants "
        "declared at signup; it is not recovered TPV, revenue or a forecast.",
        "",
        "| Metric | Value |", "|---|---|",
        *[f"| {k.replace('_', ' ')} | {v} |" for k, v in s.items() if not isinstance(v, (list, dict))],
        f"| applications by tier | {s['applications_by_tier']} |",
        f"| TPV at stake by tier (lakh) | {s['tpv_at_stake_by_tier_lakh']} |",
        "",
        "## Top three causes by number of applications", bullets(s["top3_causes_by_count"]),
        "",
        "## Top three causes by expected monthly TPV", bullets(s["top3_causes_by_tpv"]),
        "",
        "## Top fixable rejection causes (excluding abandonment)",
        "By count:", bullets(s["top3_fixable_rejections_by_count"]),
        "", "By TPV:", bullets(s["top3_fixable_rejections_by_tpv"]),
        "",
        "## Where merchants abandon without a rejection (R13)",
        "| Step | Applications | Expected monthly TPV (lakh) |", "|---|---|---|",
        *[f"| {r.step_reached} | {r.applications} | {r.expected_monthly_tpv_represented_lakh} |"
          for r in steps.itertuples()],
        "",
        "## All causes",
        "| Code | Cause | Fixable | Apps | Share % | Recoverable | TPV (lakh) | Via AI |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {r.cause_code} | {r.cause} | {r.fixability} | {r.applications} | "
          f"{r.share_of_non_activated_pct} | {r.recoverable} | {r.expected_monthly_tpv_represented_lakh} | "
          f"{r.via_ai_classification} |" for r in causes.itertuples()],
        "",
        "## HIGH-priority follow-ups",
        f"Score = {config.PRIORITY_WEIGHT_TPV} x TPV percentile + {config.PRIORITY_WEIGHT_RECENCY} x "
        "(100 - days inactive). A prototype ordering heuristic, not a recovery probability.",
        "",
        "| Rank | Application | Cause | TPV (lakh) | Days inactive | Score | Channel | Language |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {int(r.priority_rank)} | {r.application_id} | {r.diagnosed_reason_code} | "
          f"{r.expected_monthly_tpv_inr_lakh} | {r.days_since_last_activity} | {r.priority_score} | "
          f"{r.recommended_channel} | {r.preferred_language} |" for r in top.itertuples()],
        "",
        "## Weight sensitivity (top 10)",
        "| Variant | Top-10 overlap with base | Rank correlation | Top-10 expected TPV (lakh) |",
        "|---|---|---|---|",
        *[f"| {r[0]} | {r[3]} | {r[4]} | {r[6]} |" for r in sens.itertuples(index=False)],
    ]
    return "\n".join(lines) + "\n"
