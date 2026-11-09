"""The Excel file opens on a readable summary, then a short decisions table, then the full table."""
import openpyxl
import pandas as pd
import pytest

from core import pipeline
from core.output_builder import write_outputs


@pytest.fixture(scope="module")
def xlsx(tmp_path_factory):
    run = pipeline.run(llm_mode="cache")
    out = tmp_path_factory.mktemp("export")
    paths = write_outputs(run.data, run.results, run.audit, run.summary, out,
                          extra_sheets=run.extra_sheets(), front_sheets=run.front_sheets())
    return run, paths["xlsx"]


def test_sheet_order_puts_summary_first(xlsx):
    _, path = xlsx
    names = openpyxl.load_workbook(path, read_only=True).sheetnames
    assert names[:3] == ["Read me first", "Decisions", "results"]


def test_readme_numbers_match_executive_summary(xlsx):
    run, path = xlsx
    rm = pd.read_excel(path, sheet_name="Read me first", dtype=str)
    text = " ".join(rm.fillna("").astype(str).values.ravel())
    ex = run.executive
    for value in [str(ex["recoverable"]), str(ex["expected_monthly_tpv_at_stake_lakh"]), "A3051",
                  *ex["top3_causes_by_count"], *ex["top3_causes_by_tpv"]]:
        assert value in text, value
    assert "not a probability" in text and "Not recovered TPV" in text


def test_decisions_sheet_is_short_and_complete(xlsx):
    run, path = xlsx
    dec = pd.read_excel(path, sheet_name="Decisions")
    assert len(dec) == len(run.results) == 75
    assert len(dec.columns) <= 13
    assert dec["Application"].iloc[0] == run.work_queue["application_id"].iloc[0]  # priority order
    assert set(dec["Application"]) == set(run.results["application_id"])
