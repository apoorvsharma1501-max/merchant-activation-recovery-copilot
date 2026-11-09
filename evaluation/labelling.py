"""Human-labelled evaluation set (30 of the 75 non-activated applications).

  make  : build evaluation/labelling/p3_labelling_sheet.xlsx with the system's answers and
          empty yellow columns for YOUR answers (never overwrites a sheet you've started)
  score : compare your answers with the system's and write evaluation/results/label_report.md

Usage:
  .venv\\Scripts\\python -m evaluation.labelling make
  .venv\\Scripts\\python -m evaluation.labelling score

Sample design (fixed list, chosen for coverage, not at random):
  - all 4 AI-classified cases (A3022, A3028, A3051, A3081)
  - all 4 coded R10 closures and all 3 R12 compliance cases
  - one coded case for each fixable code R01-R09, R11, spread across languages
  - 9 R13 abandonment cases across every step and language
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook as open_xlsx
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

import config
from core.data_loader import load_workbook

HERE = Path(__file__).resolve().parent
SHEET = HERE / "labelling" / "p3_labelling_sheet.xlsx"
REPORT = HERE / "results" / "label_report.md"

SAMPLE = [
    # AI-classified
    "A3022", "A3028", "A3051", "A3081",
    # R10 and R12
    "A3039", "A3073", "A3093", "A3097", "A3082", "A3094", "A3096",
    # one per fixable code
    "A3004", "A3001", "A3040", "A3046", "A3064", "A3080", "A3090", "A3072", "A3023", "A3015",
    # R13 across steps and languages
    "A3005", "A3006", "A3008", "A3029", "A3050", "A3034", "A3054", "A3056", "A3098",
]

SYSTEM_COLS = [
    "application_id", "application_status", "step_reached", "preferred_language", "whatsapp_opted_in",
    "rejection_code_original", "rejection_message_original",
    "diagnosed_reason_code", "diagnosis_method", "fixability", "recoverability", "recommended_action",
    "recommended_channel", "nudge_status", "nudge_text", "nudge_english_back_translation",
]
HUMAN = {
    "H_correct_code": ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12",
                       "R13", "UNKNOWN"],
    "H_fixable": ["Yes", "No", "Needs compliance review"],
    "H_recoverability": ["RECOVERABLE", "NOT_RECOVERABLE_CLOSE", "COMPLIANCE_REVIEW", "NEEDS_HUMAN_REVIEW"],
    "H_channel_ok": ["Yes", "No"],
    "H_message_should_exist": ["Yes", "No"],
    "H_message_meaning_ok": ["Yes", "No", "NA"],
    "H_message_tone_ok": ["Yes", "No", "NA"],
    "H_message_problem": ["None", "Promise/timeline", "Adds advice not in catalog", "Compliance leak",
                          "Workaround", "Wrong language/script", "Unclear action", "Other"],
    "H_language_checked_by": ["Me (I read this language)", "Native speaker", "Back-translation only", "NA"],
    "H_notes": None,
}

INSTRUCTIONS = [
    "HOW TO LABEL (about 30-40 minutes)",
    "",
    "1. Work through the 'cases' sheet. Grey columns are what the system decided. Yellow columns are YOURS.",
    "2. Decide each yellow column from the source data and the 'catalog' sheet - before looking at the system's",
    "   answer if you can. Use the dropdowns.",
    "3. H_correct_code: the catalog code you believe is right (UNKNOWN if the evidence is not enough).",
    "4. H_fixable / H_recoverability: what the catalog and the brief imply for this case.",
    "5. H_channel_ok: WhatsApp only if the merchant opted in; compliance cases manual only.",
    "6. H_message_should_exist: should a merchant message be drafted at all right now?",
    "7. Message columns: judge the draft. If you cannot read the language, judge the back-translation and set",
    "   H_language_checked_by = 'Back-translation only' - ideally ask a native speaker for Tamil/Kannada/Marathi.",
    "8. Write anything surprising in H_notes. Save the file, then tell Claude to score it.",
    "",
    "These are YOUR labels - the brief requires individual work and that you can explain every choice.",
    "Agreement with your labels is NOT accuracy against the organisers' hidden key; report it as such.",
]


def make() -> Path:
    if SHEET.exists():
        print(f"Sheet already exists, not overwriting: {SHEET}")
        return SHEET
    res = pd.read_csv(config.OUTPUT_DIR / "p3_results.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    missing = [i for i in SAMPLE if i not in set(res["application_id"])]
    if missing:
        raise SystemExit(f"Sample IDs not in results: {missing}")
    cases = res.set_index("application_id").loc[SAMPLE].reset_index()[SYSTEM_COLS]
    for col in HUMAN:
        cases[col] = ""
    catalog = load_workbook(config.DEFAULT_WORKBOOK).catalog
    cat = pd.DataFrame([{"code": e.code, "reviewer_reason": e.reviewer_reason, "meaning": e.plain_language_meaning,
                         "fixable": e.fixable_raw, "standard_fix": e.standard_fix} for e in catalog.values()])

    SHEET.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(SHEET, engine="openpyxl") as xw:
        pd.DataFrame({"instructions": INSTRUCTIONS}).to_excel(xw, sheet_name="instructions", index=False)
        cases.to_excel(xw, sheet_name="cases", index=False)
        cat.to_excel(xw, sheet_name="catalog", index=False)

    wb = open_xlsx(SHEET)
    ws = wb["cases"]
    grey, yellow = PatternFill("solid", fgColor="EDEDED"), PatternFill("solid", fgColor="FFF2B3")
    header = [c.value for c in ws[1]]
    n = ws.max_row
    for idx, name in enumerate(header, start=1):
        letter = ws.cell(1, idx).column_letter
        human = name in HUMAN
        ws.cell(1, idx).font = Font(bold=True)
        for r in range(1, n + 1):
            cell = ws.cell(r, idx)
            cell.fill = yellow if human else grey
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[letter].width = 46 if name in ("nudge_text", "nudge_english_back_translation",
                                                            "rejection_message_original", "H_notes") else 18
        if human and HUMAN[name]:
            dv = DataValidation(type="list", formula1='"' + ",".join(HUMAN[name]) + '"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{letter}2:{letter}{n}")
    ws.freeze_panes = "B2"
    wb["instructions"].column_dimensions["A"].width = 120
    wb["catalog"].column_dimensions["E"].width = 90
    wb.save(SHEET)
    print(f"Labelling sheet written: {SHEET} ({len(cases)} cases)")
    return SHEET


def _agree(df: pd.DataFrame, human: str, system: str) -> tuple[int, int, pd.DataFrame]:
    labelled = df[df[human].str.strip() != ""]
    mism = labelled[labelled[human].str.strip() != labelled[system].str.strip()]
    return len(labelled) - len(mism), len(labelled), mism


def score() -> str:
    if not SHEET.exists():
        raise SystemExit("No labelling sheet yet - run `make` first.")
    df = pd.read_excel(SHEET, sheet_name="cases", dtype=str).fillna("")
    df["system_message_exists"] = df["nudge_status"].isin(["DRAFTED", "NEUTRAL_COMPLIANCE"]).map(
        {True: "Yes", False: "No"})
    checks = [("Diagnosis code", "H_correct_code", "diagnosed_reason_code"),
              ("Fixability", "H_fixable", "fixability"),
              ("Recoverability", "H_recoverability", "recoverability"),
              ("Message should exist", "H_message_should_exist", "system_message_exists")]
    lines = ["# Human-labelled evaluation (30 cases)", "",
             "Agreement between the system and the student's own labels. Not accuracy against the "
             "organisers' hidden answer key.", "",
             "| Dimension | Agree | Labelled | Agreement |", "|---|---|---|---|"]
    mismatches = []
    for name, h, s in checks:
        ok, total, mism = _agree(df, h, s)
        lines.append(f"| {name} | {ok} | {total} | {ok / total:.0%} |" if total else f"| {name} | - | 0 | - |")
        for r in mism.itertuples():
            mismatches.append(f"| {r.application_id} | {name} | {getattr(r, s)} | {getattr(r, h)} | {r.H_notes} |")
    for name, col in [("Channel correct", "H_channel_ok"), ("Message meaning OK", "H_message_meaning_ok"),
                      ("Message tone OK", "H_message_tone_ok")]:
        vals = df[col][df[col].isin(["Yes", "No"])]
        if len(vals):
            lines.append(f"| {name} | {int((vals == 'Yes').sum())} | {len(vals)} | {(vals == 'Yes').mean():.0%} |")
    probs = df["H_message_problem"][~df["H_message_problem"].isin(["", "None"])]
    checked = df["H_language_checked_by"].value_counts().to_dict()
    lines += ["", f"Message problems found: {len(probs)} " + (f"({probs.value_counts().to_dict()})" if len(probs) else ""),
              f"How languages were checked: {checked}", "",
              "## Disagreements", "| Case | Dimension | System | Human | Notes |", "|---|---|---|---|---|",
              *(mismatches or ["| - | none | | | |"])]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return str(REPORT)


if __name__ == "__main__":
    {"make": make, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "make"]()
