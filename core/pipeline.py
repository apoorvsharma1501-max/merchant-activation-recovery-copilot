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
