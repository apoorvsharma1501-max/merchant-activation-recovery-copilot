"""Phase 1 data-quality profile. Every number is computed from the loaded workbook."""
from __future__ import annotations

import config
from core.data_loader import LoadedData


def profile(data: LoadedData) -> dict:
    apps = data.applications
    non_act = apps[apps["application_status"] != config.STATUS_ACTIVATED]
    blank = apps["rejection_code"].isna()
    has_msg = apps["rejection_message"].notna()
    tpv = apps["expected_monthly_tpv_inr_lakh"]
    days = apps["days_since_last_activity"]
    return {
        "source_file": data.source_file,
        "total_applications": len(apps),
        "status_counts": apps["application_status"].value_counts(dropna=False).to_dict(),
        "non_activated": len(non_act),
        "catalog_codes": sorted(data.catalog),
        "blank_code_all_rows": int(blank.sum()),
        "blank_code_by_status": apps[blank]["application_status"].value_counts().to_dict(),
        "blank_code_with_reviewer_text": apps[blank & has_msg][
            ["application_id", "application_status", "rejection_message"]].to_dict("records"),
        "blank_code_no_text_non_activated": int(
            (blank & ~has_msg & apps["application_status"].ne(config.STATUS_ACTIVATED)).sum()),
        "code_counts_non_activated": non_act["rejection_code"].value_counts().sort_index().to_dict(),
        "language_counts": apps["preferred_language"].value_counts(dropna=False).to_dict(),
        "whatsapp_opt_in": apps["whatsapp_opt_in_normalized"].value_counts().to_dict(),
        "step_counts_non_activated": non_act["step_reached"].value_counts(dropna=False).to_dict(),
        "tpv_range": (tpv.min(), tpv.max()),
        "tpv_missing_or_invalid": int(tpv.isna().sum()),
        "days_range": (days.min(), days.max()),
        "days_missing_or_invalid": int(days.isna().sum()),
        "inactivity_exceeds_account_age": int(apps["activity_consistency_flag"].notna().sum()),
        "activated_with_code_or_text":int((apps["application_status"].eq(config.STATUS_ACTIVATED)
                                            & (~blank | has_msg)).sum()),
        "issues": [i.__dict__ for i in data.issues],
    }


def to_markdown(p: dict) -> str:
    def kv(d: dict) -> str:
        return "\n".join(f"| {k} | {v} |" for k, v in d.items())

    lines = [
        "# P3 data-quality report",
        "",
        f"Source: `{p['source_file']}` (generated at runtime; nothing hard-coded).",
        "",
        "## Overview",
        "| Item | Value |", "|---|---|",
        f"| Total applications | {p['total_applications']} |",
        f"| Non-activated (in scope) | {p['non_activated']} |",
        f"| Catalog codes | {len(p['catalog_codes'])}: {', '.join(p['catalog_codes'])} |",
        f"| Blank rejection code (all rows) | {p['blank_code_all_rows']} |",
        f"| Blank code, no reviewer text, non-activated | {p['blank_code_no_text_non_activated']} |",
        f"| Expected monthly TPV range (Rs lakh) | {p['tpv_range'][0]} to {p['tpv_range'][1]} |",
        f"| TPV missing/invalid | {p['tpv_missing_or_invalid']} |",
        f"| Days since activity range | {p['days_range'][0]} to {p['days_range'][1]} |",
        f"| Days missing/invalid | {p['days_missing_or_invalid']} |",
        f"| Activated rows carrying a code or reviewer text | {p['activated_with_code_or_text']} |",
        f"| Rows where inactivity > days since signup (snapshot) | {p['inactivity_exceeds_account_age']} |",
        "",
        "## Status", "| Status | Count |", "|---|---|", kv(p["status_counts"]),
        "",
        "## Blank code by status", "| Status | Count |", "|---|---|", kv(p["blank_code_by_status"]),
        "",
        "## Blank code but reviewer text present (needs text classification)",
        "| Application | Status | Reviewer text |", "|---|---|---|",
        *[f"| {r['application_id']} | {r['application_status']} | {r['rejection_message']} |"
          for r in p["blank_code_with_reviewer_text"]],
        "",
        "## Rejection codes among non-activated", "| Code | Count |", "|---|---|",
        kv(p["code_counts_non_activated"]),
        "",
        "## Step reached (non-activated)", "| Step | Count |", "|---|---|", kv(p["step_counts_non_activated"]),
        "",
        "## Preferred language", "| Language | Count |", "|---|---|", kv(p["language_counts"]),
        "",
        "## WhatsApp opt-in", "| Value | Count |", "|---|---|", kv(p["whatsapp_opt_in"]),
        "",
        f"## Validation issues ({len(p['issues'])})",
    ]
    if p["issues"]:
        lines += ["| Severity | Sheet | Row | Field | Message |", "|---|---|---|---|---|"]
        lines += [f"| {i['severity']} | {i['sheet']} | {i['row_key']} | {i['field']} | {i['message']} |"
                  for i in p["issues"]]
    else:
        lines.append("None found.")
    return "\n".join(lines) + "\n"
