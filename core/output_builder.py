"""Build the one-row-per-non-activated-application output table (handover section 10)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config
from core import ai_diagnosis, nudge_generator, prioritization, rules
from core.data_loader import LoadedData
from core.llm_client import CachedLLM
from schemas.labels import NudgeStatus, Recoverability

OUTPUT_COLUMNS = [
    # source fields (original values, unmodified)
    "application_id", "application_status", "step_reached", "business_type", "industry",
    "preferred_language", "expected_monthly_tpv_inr_lakh", "days_since_last_activity",
    "whatsapp_opted_in", "rejection_code_original", "rejection_message_original",
    # diagnosis
    "diagnosed_reason_code", "diagnosed_reason", "diagnosis_status", "diagnosis_method",
    "diagnosis_evidence", "ai_explanation", "fixability", "recoverability", "recommended_action",
    "human_review_required", "review_reasons",
    # channel and nudge
    "recommended_channel", "whatsapp_allowed", "nudge_language", "language_status",
    "nudge_brief", "nudge_text", "nudge_english_back_translation", "nudge_status",
    "nudge_safety_check_passed", "nudge_safety_issues", "nudge_review_required",
    # prioritisation (Phase 4)
    "tpv_percentile", "recency_score", "priority_score", "priority_rank", "priority_tier", "priority_status",
    # provenance
    "data_flags", "diagnosis_model", "prompt_version", "nudge_model", "nudge_prompt_version",
    "rule_version", "run_timestamp_utc", "source_file",
]


def _raw(value):
    """Original cell value for display; NaN becomes empty."""
    return None if pd.isna(value) else value


def build_results(data: LoadedData, llm: CachedLLM | None = None,
                  run_timestamp: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (results for non-activated applications, audit table of activated applications).

    `llm=None` (or mode "off") runs rules only: blank-code text stays in human review and only
    English rows get a (template) message.
    """
    run_timestamp = run_timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    apps, raw = data.applications, data.applications_raw
    rows, audit = [], []
    use_ai = llm is not None and llm.enabled

    for idx in apps.index:
        row = apps.loc[idx].to_dict()
        src = raw.loc[idx]
        if not rules.is_in_scope(row["application_status"]):
            audit.append({"application_id": row["application_id"],
                          "application_status": row["application_status"],
                          "step_reached": row["step_reached"],
                          "recovery_action": "None - activated applications receive no nudge"})
            continue

        dx = rules.diagnose(row, data.catalog)
        if dx.pending_ai and use_ai:
            dx = ai_diagnosis.classify(row, dx, data.catalog, llm)
        dec = rules.decide(dx, data.catalog)
        entry = data.catalog.get(dx.code)
        language, lang_status = rules.language_for(row["preferred_language"])
        channel = rules.select_channel(bool(row["whatsapp_allowed"]), dec.recoverability)
        nudge = nudge_generator.generate(row, dx, dec, entry, llm)

        if dx.sensitive and dec.human_review:
            reason_text = "Sensitive case - details withheld pending human/compliance review"
        elif entry is not None:
            reason_text = entry.plain_language_meaning
        else:
            reason_text = "Undetermined - human review required"

        flags = [row[f"{c}__flag"] for c in config.APPLICATION_NUMERIC_COLUMNS if row[f"{c}__flag"]]
        if row["whatsapp_opt_in_normalized"] in {"Missing", "Unrecognized"}:
            flags.append(f"whatsapp_opted_in {row['whatsapp_opt_in_normalized'].lower()}")

        rows.append({
            "application_id": row["application_id"],
            "application_status": _raw(src["application_status"]),
            "step_reached": _raw(src["step_reached"]),
            "business_type": _raw(src["business_type"]),
            "industry": _raw(src["industry"]),
            "preferred_language": _raw(src["preferred_language"]),
            "expected_monthly_tpv_inr_lakh": _raw(src["expected_monthly_tpv_inr_lakh"]),
            "days_since_last_activity": _raw(src["days_since_last_activity"]),
            "whatsapp_opted_in": _raw(src["whatsapp_opted_in"]),
            "rejection_code_original": _raw(src["rejection_code"]),
            "rejection_message_original": _raw(src["rejection_message"]),
            "diagnosed_reason_code": dx.code,
            "diagnosed_reason": reason_text,
            "diagnosis_status": dx.status.value,
            "diagnosis_method": dx.method.value,
            "diagnosis_evidence": dx.evidence,
            "ai_explanation": dx.ai_explanation or None,
            "fixability": dec.fixability.value,
            "recoverability": dec.recoverability.value,
            "recommended_action": dec.action.value,
            "human_review_required": dec.human_review,
            "review_reasons": "; ".join(dec.review_reasons),
            "recommended_channel": channel,
            "whatsapp_allowed": bool(row["whatsapp_allowed"]),
            "nudge_language": language,
            "language_status": lang_status.value,
            "nudge_brief": rules.message_brief(dec, dx, entry, row["step_reached"]),
            "nudge_text": nudge.text,
            "nudge_english_back_translation": nudge.back_translation,
            "nudge_status": nudge.status.value,
            "nudge_safety_check_passed": nudge.safety_passed,
            "nudge_safety_issues": "; ".join(nudge.issues),
            "nudge_review_required": True,  # every draft needs human approval; nothing is sent
            # filled by prioritization.score() below
            "data_flags": "; ".join(flags),
            "diagnosis_model": dx.model,
            "prompt_version": dx.prompt_version,
            "nudge_model": nudge.model,
            "nudge_prompt_version": nudge.prompt_version,
            "rule_version": config.RULE_VERSION,
            "run_timestamp_utc": run_timestamp,
            "source_file": data.source_file,
        })

    results = prioritization.score(pd.DataFrame(rows).reindex(columns=OUTPUT_COLUMNS))
    return results[OUTPUT_COLUMNS], pd.DataFrame(audit)


def coverage_summary(data: LoadedData, results: pd.DataFrame) -> dict:
    apps = data.applications
    rec = results["recoverability"].value_counts().to_dict()
    recoverable = results[results["recoverability"] == Recoverability.RECOVERABLE.value]
    return {
        "total_applications": len(apps),
        "activated": int((apps["application_status"] == config.STATUS_ACTIVATED).sum()),
        "stalled": int((apps["application_status"] == config.STATUS_STALLED).sum()),
        "rejected": int((apps["application_status"] == config.STATUS_REJECTED).sum()),
        "non_activated_processed": len(results),
        "recoverable": rec.get(Recoverability.RECOVERABLE.value, 0),
        "not_recoverable_close": rec.get(Recoverability.NOT_RECOVERABLE_CLOSE.value, 0),
        "compliance_review": rec.get(Recoverability.COMPLIANCE_REVIEW.value, 0),
        "needs_human_review": rec.get(Recoverability.NEEDS_HUMAN_REVIEW.value, 0),
        "human_review_required_flag": int(results["human_review_required"].sum()),
        "pending_text_classification": int(((results["diagnosis_status"] == "NEEDS_HUMAN_REVIEW")
                                            & results["rejection_message_original"].notna()).sum()),
        "expected_monthly_tpv_at_stake_inr_lakh": round(float(
            pd.to_numeric(recoverable["expected_monthly_tpv_inr_lakh"], errors="coerce").sum()), 2),
        "actions": results["recommended_action"].value_counts().to_dict(),
        "diagnosis_methods": results["diagnosis_method"].value_counts().to_dict(),
        "nudge_status": results["nudge_status"].value_counts().to_dict(),
        "nudge_safety_failures": int((results["nudge_safety_check_passed"] == False).sum()),  # noqa: E712
        "nudges_drafted": int(results["nudge_status"].isin(
            [NudgeStatus.DRAFTED.value, NudgeStatus.NEUTRAL_COMPLIANCE.value]).sum()),
    }


def write_outputs(data: LoadedData, results: pd.DataFrame, audit: pd.DataFrame,
                  summary: dict, out_dir: Path = config.OUTPUT_DIR,
                  extra_sheets: dict[str, pd.DataFrame] | None = None) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "p3_results.csv"
    xlsx_path = out_dir / "p3_results.xlsx"
    # utf-8-sig so Excel shows Hindi/Tamil/Kannada/Marathi text correctly.
    results.to_csv(csv_path, index=False, encoding="utf-8-sig")
    issues = pd.DataFrame([i.__dict__ for i in data.issues],
                          columns=["severity", "sheet", "row_key", "field", "message"])
    summary_rows = [(k, v if not isinstance(v, dict) else "; ".join(f"{a}: {b}" for a, b in v.items()))
                    for k, v in summary.items()]
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xw:
        results.to_excel(xw, sheet_name="results", index=False)
        pd.DataFrame(summary_rows, columns=["metric", "value"]).to_excel(xw, sheet_name="summary", index=False)
        for name, frame in (extra_sheets or {}).items():
            frame.to_excel(xw, sheet_name=name[:31], index=False)
        audit.to_excel(xw, sheet_name="activated_audit", index=False)
        issues.to_excel(xw, sheet_name="data_issues", index=False)
    return {"csv": csv_path, "xlsx": xlsx_path}
