"""One function that runs the whole analysis; used by the CLI and the Streamlit app."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import config
from core import analytics, prioritization
from core.data_loader import LoadedData, load_workbook
from core.data_profile import profile
from core.llm_client import CachedLLM, build_llm
from core.output_builder import build_results, coverage_summary

QUEUE_COLUMNS = ["priority_rank", "priority_tier", "application_id", "diagnosed_reason_code",
                 "recommended_action", "expected_monthly_tpv_inr_lakh", "days_since_last_activity",
                 "priority_score", "recommended_channel", "preferred_language", "nudge_status"]


DECISION_COLUMNS = {
    "priority_rank": "Priority rank",
    "priority_tier": "Priority tier",
    "application_id": "Application",
    "application_status": "Status",
    "step_reached": "Stuck at step",
    "diagnosed_reason_code": "Cause code",
    "diagnosed_reason": "Cause (plain language)",
    "recoverability": "Decision",
    "recommended_action": "Next action",
    "recommended_channel": "Channel",
    "preferred_language": "Language",
    "expected_monthly_tpv_inr_lakh": "Expected monthly TPV (Rs lakh)",
    "nudge_text": "Draft message (needs approval)",
}


@dataclass
class PipelineRun:
    data: LoadedData
    results: pd.DataFrame
    audit: pd.DataFrame
    summary: dict
    causes: pd.DataFrame
    steps: pd.DataFrame
    sensitivity: pd.DataFrame
    executive: dict
    profile: dict
    llm: CachedLLM

    @property
    def work_queue(self) -> pd.DataFrame:
        r = self.results
        return r[r["priority_status"] == "OK"].sort_values("priority_rank")[QUEUE_COLUMNS]

    def decisions_sheet(self) -> pd.DataFrame:
        """One row per non-activated application, only the columns a reader needs, priority order."""
        r = self.results.assign(_r=self.results["priority_rank"].fillna(10_000)).sort_values(["_r", "application_id"])
        out = r[list(DECISION_COLUMNS)].rename(columns=DECISION_COLUMNS)
        out["Priority rank"] = out["Priority rank"].map(lambda v: "" if pd.isna(v) else int(v))
        return out.reset_index(drop=True)

    def readme_sheet(self) -> pd.DataFrame:
        """Front page of the Excel file: what it is, headline numbers, top causes, HIGH list."""
        ex, r = self.executive, self.results
        n_rule = int(r["diagnosis_method"].isin(["CATALOG_RULE", "INACTIVITY_RULE"]).sum())
        n_ai = int((r["diagnosis_method"] == "LLM_TEXT_CLASSIFICATION").sum())
        rows = [
            ("About", "What this file is", "Output of the Merchant Activation Recovery & Diagnosis Copilot for Razorpay "
             "Campus AI Build-a-thon Problem 3, run on the supplied synthetic data pack."),
            ("About", "How to read it", "'Decisions' = one row per non-activated application with the key fields. "
             "'results' = every field. Other sheets: work queue, causes, sensitivity, data issues."),
            ("Headline", "Applications in the data", ex["total_applications"]),
            ("Headline", "Activated / Stalled / Rejected", f"{ex['activated']} / {ex['stalled']} / {ex['rejected']}"),
            ("Headline", "Non-activated applications processed", ex["non_activated_processed"]),
            ("Headline", "Recoverable", ex["recoverable"]),
            ("Headline", "Close: restricted category (no workaround offered)", ex["not_recoverable_close"]),
            ("Headline", "Compliance review (neutral message, manual channel)", ex["compliance_review"]),
            ("Headline", "Flagged for human confirmation before any message",
             f"{ex['human_review_flagged']} ({', '.join(r.loc[r['human_review_required'], 'application_id'])})"),
            ("Headline", "Expected monthly TPV at stake, recoverable (Rs lakh)", ex["expected_monthly_tpv_at_stake_lakh"]),
            ("Headline", "Messages drafted for human approval",
             f"{int(r['nudge_status'].isin(['DRAFTED', 'NEUTRAL_COMPLIANCE']).sum())} in "
             f"{r.loc[r['nudge_text'].notna(), 'preferred_language'].nunique()} languages; nothing is sent automatically"),
            ("Headline", "WhatsApp recommended (opted in only)", int((r["recommended_channel"] == "WhatsApp").sum())),
        ]
        rows += [("Top causes by count", f"{i}.", c) for i, c in enumerate(ex["top3_causes_by_count"], 1)]
        rows += [("Top causes by expected TPV", f"{i}.", c) for i, c in enumerate(ex["top3_causes_by_tpv"], 1)]
        high = r[r["priority_tier"] == "HIGH"].sort_values("priority_rank")
        tier_tpv = ex["tpv_at_stake_by_tier_lakh"].get("HIGH", 0)
        rows.append(("HIGH priority", f"{len(high)} applications",
                     f"{tier_tpv} lakh = {tier_tpv / ex['expected_monthly_tpv_at_stake_lakh']:.0%} of TPV at stake"))
        rows += [("HIGH priority", f"{int(h.priority_rank)}. {h.application_id} ({h.diagnosed_reason_code})",
                  f"{h.expected_monthly_tpv_inr_lakh} lakh, {h.days_since_last_activity} days inactive, "
                  f"{h.recommended_channel}, {h.preferred_language}") for h in high.itertuples()]
        rows += [
            ("Read with care", "Expected monthly TPV", "Declared by merchants at signup. Not recovered TPV, revenue or a forecast."),
            ("Read with care", "Priority score", "0.7 x TPV percentile + 0.3 x (100 - days inactive). A ranking aid, "
             "not a probability of activation."),
            ("Read with care", "Decided by",
             f"Rules decide {n_rule} of {len(r)} cases from the rejection catalog; AI reads {n_ai} free-text reviewer "
             "notes (quoting the exact words) and drafts the messages. A person approves everything."),
        ]
        return pd.DataFrame(rows, columns=["Section", "Item", "Value"])

    def front_sheets(self) -> dict[str, pd.DataFrame]:
        return {"Read me first": self.readme_sheet(), "Decisions": self.decisions_sheet()}

    def extra_sheets(self) -> dict[str, pd.DataFrame]:
        return {"work_queue": self.work_queue, "causes": self.causes,
                "abandonment_by_step": self.steps, "priority_sensitivity": self.sensitivity}


def run(workbook: str | Path = config.DEFAULT_WORKBOOK, llm_mode: str | None = None,
        llm: CachedLLM | None = None) -> PipelineRun:
    data = load_workbook(workbook)
    llm = llm or build_llm(llm_mode)
    try:
        results, audit = build_results(data, llm)
    finally:
        if llm.mode == "live":
            llm.save()  # keep whatever was paid for, even if the run stops part-way
    summary = coverage_summary(data, results)
    summary["ai_usage"] = llm.usage_summary()
    causes = analytics.cause_table(results, data)
    return PipelineRun(
        data=data, results=results, audit=audit, summary=summary, causes=causes,
        steps=analytics.abandonment_by_step(results),
        sensitivity=prioritization.sensitivity(results),
        executive=analytics.executive_summary(data, results, causes),
        profile=profile(data), llm=llm,
    )
