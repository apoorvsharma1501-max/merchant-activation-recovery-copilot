"""Stress test of the AI reviewer-note classifier on hand-written tricky notes.

The notes in `stress_notes.csv` are synthetic and were written to break the system:
paraphrases, Hindi/Tamil script, typos, two problems in one note, negation traps,
compliance euphemisms, words that falsely trip the keyword guard, vague notes and
prompt-injection attempts. Expected answers were set when the notes were written,
before running the system.

Usage:
  .venv\\Scripts\\python -m evaluation.stress_test            # live if a key is set, else saved answers
  .venv\\Scripts\\python -m evaluation.stress_test --llm cache

Outcomes per case:
  PASS            right code (or acceptable alternative) and held for review when it must be
  CRITICAL_MISS   a restricted/compliance case was NOT held - a merchant message could go out
  MISSED_REVIEW   an ambiguous/multi-issue case was not held for review
  WRONG_CODE      wrong catalog code on a case that is not safety-critical
  OVER_CAUTIOUS   right code but held for review unnecessarily (safe, costs reviewer time)
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

import config
from core import ai_diagnosis, nudge_generator, rules
from core.data_loader import load_workbook
from core.llm_client import AnthropicLLM, CachedLLM
from schemas.labels import CODE_NEEDS_HUMAN_REVIEW, CODE_UNKNOWN, Recoverability

HERE = Path(__file__).resolve().parent
NOTES = HERE / "stress_notes.csv"
OUT_DIR = HERE / "results"
CACHE = config.ROOT / "cache" / "stress_llm_cache.json"


def _bool(v) -> bool:
    return str(v).strip().lower() == "true"


def evaluate_case(case: pd.Series, catalog, llm: CachedLLM) -> dict:
    row = {"application_id": case["case_id"], "rejection_code": None, "rejection_message": case["note"],
           "application_status": config.STATUS_STALLED, "step_reached": "KYC docs",
           "days_since_last_activity": 10.0}
    rule_dx = rules.diagnose(row, catalog)
    dx = ai_diagnosis.classify(row, rule_dx, catalog, llm)
    dec = rules.decide(dx, catalog)
    held = nudge_generator.should_withhold(dx, dec) or dec.recoverability is Recoverability.COMPLIANCE_REVIEW

    acceptable = set(str(case["acceptable_codes"]).split("|"))
    code = dx.code if dx.code != CODE_NEEDS_HUMAN_REVIEW else CODE_UNKNOWN  # failed AI = undetermined
    code_ok = code in acceptable
    must_review, sensitive = _bool(case["must_review"]), _bool(case["expect_sensitive"])

    if sensitive and not held:
        outcome = "CRITICAL_MISS"
    elif must_review and not held:
        outcome = "MISSED_REVIEW"
    elif not code_ok:
        outcome = "WRONG_CODE"
    elif held and not must_review:
        outcome = "OVER_CAUTIOUS"
    else:
        outcome = "PASS"

    return {
        "case_id": case["case_id"], "category": case["category"], "note": case["note"],
        "expected_code": case["expected_code"], "acceptable_codes": case["acceptable_codes"],
        "must_review": must_review, "expect_sensitive": sensitive,
        "system_code": dx.code, "diagnosis_status": dx.status.value,
        "recoverability": dec.recoverability.value, "held_for_review": held,
        "sensitive_flag": dx.sensitive, "guard_matched": rules.is_sensitive_text(case["note"]),
        "evidence": dx.evidence, "ai_explanation": dx.ai_explanation,
        "review_reasons": "; ".join(dx.review_reasons), "outcome": outcome, "why_this_case": case["why"],
    }


def report(df: pd.DataFrame, usage: dict) -> str:
    n = len(df)
    counts = df["outcome"].value_counts()
    safe = n - counts.get("CRITICAL_MISS", 0) - counts.get("MISSED_REVIEW", 0)
    by_cat = df.groupby("category")["outcome"].agg(
        cases="count", passed=lambda s: int((s == "PASS").sum()),
        problems=lambda s: ", ".join(sorted(set(x for x in s if x != "PASS"))) or "-")
    lines = [
        "# Stress test: AI reviewer-note classifier",
        "",
        f"{n} hand-written synthetic notes designed to break the classifier. Expected answers were fixed "
        "before the run. This measures agreement with *our* expected labels, not the organisers' hidden key.",
        "",
        "| Outcome | Cases |", "|---|---|",
        *[f"| {k} | {counts.get(k, 0)} |" for k in
          ["PASS", "OVER_CAUTIOUS", "WRONG_CODE", "MISSED_REVIEW", "CRITICAL_MISS"]],
        "",
        f"- Strict pass rate: **{counts.get('PASS', 0)}/{n} ({counts.get('PASS', 0) / n:.0%})**",
        f"- Safe outcome (no missed review, no critical miss): **{safe}/{n} ({safe / n:.0%})**",
        f"- Critical misses (compliance/restricted case not held): **{counts.get('CRITICAL_MISS', 0)}**",
        f"- Model: {usage['model']} · API calls {usage['api_calls']} · saved answers reused {usage['cache_hits']} · "
        f"tokens in/out {usage['input_tokens']:,}/{usage['output_tokens']:,}",
        "",
        "## By category", "| Category | Cases | Passed | Problems |", "|---|---|---|---|",
        *[f"| {c} | {r.cases} | {r.passed} | {r.problems} |" for c, r in by_cat.iterrows()],
        "",
        "## Every case that did not pass",
        "| Case | Note | Expected | System | Held? | Outcome | Notes |", "|---|---|---|---|---|---|---|",
        *[f"| {r.case_id} | {r.note} | {r.acceptable_codes} | {r.system_code} | {r.held_for_review} | "
          f"{r.outcome} | {r.review_reasons or r.ai_explanation} |"
          for r in df[df["outcome"] != "PASS"].itertuples()],
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    load_dotenv(config.ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", choices=["live", "cache"], default=None)
    args = parser.parse_args()
    mode = args.llm or ("live" if os.environ.get("ANTHROPIC_API_KEY") else "cache")
    llm = CachedLLM(inner=AnthropicLLM() if mode == "live" else None, mode=mode, cache_path=CACHE)

    catalog = load_workbook(config.DEFAULT_WORKBOOK).catalog
    cases = pd.read_csv(NOTES, dtype=str, keep_default_na=False)
    try:
        rows = [evaluate_case(c, catalog, llm) for _, c in cases.iterrows()]
    finally:
        if mode == "live":
            llm.save()
    df = pd.DataFrame(rows)
    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_DIR / "stress_results.csv", index=False, encoding="utf-8-sig")
    md = report(df, llm.usage_summary())
    (OUT_DIR / "stress_report.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
