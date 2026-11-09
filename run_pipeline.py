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
from core import analytics, pipeline
from core.data_profile import to_markdown
from core.output_builder import write_outputs


def main() -> None:
    load_dotenv(config.ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workbook", default=str(config.DEFAULT_WORKBOOK))
    parser.add_argument("--out", default=str(config.OUTPUT_DIR))
    parser.add_argument("--llm", choices=["live", "cache", "off"], default=None)
    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    run = pipeline.run(args.workbook, args.llm)

    report = out_dir / "data_quality_report.md"
    report.write_text(to_markdown(run.profile), encoding="utf-8")
    exec_md = out_dir / "executive_summary.md"
    exec_md.write_text(analytics.summary_markdown(run.executive, run.causes, run.steps, run.sensitivity,
                                                  run.results), encoding="utf-8")
    paths = write_outputs(run.data, run.results, run.audit, run.summary, out_dir,
                          extra_sheets=run.extra_sheets(), front_sheets=run.front_sheets())

    print(json.dumps(run.summary, indent=2, default=str, ensure_ascii=False))
    print(json.dumps(run.executive, indent=2, default=str, ensure_ascii=False))
    print(f"\nExecutive summary: {exec_md}")
    print(f"Data-quality report: {report}")
    for kind, path in paths.items():
        print(f"Results ({kind}): {path}")


if __name__ == "__main__":
    main()
