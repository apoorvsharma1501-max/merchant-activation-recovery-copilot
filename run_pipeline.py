"""Command-line run: profile the workbook, apply rules (+ AI if enabled), write outputs.

Usage:
  .venv\\Scripts\\python run_pipeline.py                 # live if ANTHROPIC_API_KEY is set, else cache-only
  .venv\\Scripts\\python run_pipeline.py --llm off       # rules only
  .venv\\Scripts\\python run_pipeline.py --llm cache     # reuse saved AI answers, never call the API
  .venv\\Scripts\\python run_pipeline.py --llm live      # call the API for anything not cached
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

import config
from core import analytics, prioritization
from core.data_loader import load_workbook
from core.data_profile import profile, to_markdown
from core.llm_client import build_llm
from core.output_builder import build_results, coverage_summary, write_outputs


def main() -> None:
    load_dotenv(config.ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workbook", default=str(config.DEFAULT_WORKBOOK))
    parser.add_argument("--out", default=str(config.OUTPUT_DIR))
    parser.add_argument("--llm", choices=["live", "cache", "off"], default=None)
    args = parser.parse_args()
    out_dir = Path(args.out)

    data = load_workbook(args.workbook)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "data_quality_report.md"
    report.write_text(to_markdown(profile(data)), encoding="utf-8")

    llm = build_llm(args.llm)
    try:
        results, audit = build_results(data, llm)
    finally:
        if llm.mode == "live":
            llm.save()  # keep whatever was paid for, even if the run stops part-way
    summary = coverage_summary(data, results)
    summary["ai_usage"] = llm.usage_summary()

    causes = analytics.cause_table(results, data)
    steps = analytics.abandonment_by_step(results)
    sens = prioritization.sensitivity(results)
    exec_summary = analytics.executive_summary(data, results, causes)
    exec_md = out_dir / "executive_summary.md"
    exec_md.write_text(analytics.summary_markdown(exec_summary, causes, steps, sens, results), encoding="utf-8")

    queue = (results[results["priority_status"] == "OK"].sort_values("priority_rank")
             [["priority_rank", "priority_tier", "application_id", "diagnosed_reason_code", "recommended_action",
               "expected_monthly_tpv_inr_lakh", "days_since_last_activity", "priority_score",
               "recommended_channel", "preferred_language", "nudge_status"]])
    paths = write_outputs(data, results, audit, summary, out_dir, extra_sheets={
        "work_queue": queue, "causes": causes, "abandonment_by_step": steps, "priority_sensitivity": sens,
    })

    print(json.dumps(summary, indent=2, default=str, ensure_ascii=False))
    print(json.dumps(exec_summary, indent=2, default=str, ensure_ascii=False))
    print(f"\nExecutive summary: {exec_md}")
    print(f"Data-quality report: {report}")
    for kind, path in paths.items():
        print(f"Results ({kind}): {path}")


if __name__ == "__main__":
    main()
