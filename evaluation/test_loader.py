"""Workbook loading and validation."""
import pandas as pd
import pytest

import config
from core.data_loader import DataValidationError, load_workbook
from evaluation.test_data import write_workbook


def _apps():
    return pd.read_excel(config.DEFAULT_WORKBOOK, sheet_name=config.APPLICATIONS_SHEET,
                         dtype=object).dropna(how="all").reset_index(drop=True)


def test_real_workbook_loads_with_expected_shape(real_data):
    assert len(real_data.applications) == 100
    assert sorted(real_data.catalog) == [f"R{i:02d}" for i in range(1, 14)]
    assert not [i for i in real_data.issues if i.severity == "ERROR"]


def test_catalog_keeps_compliance_fixability_distinct(catalog):
    assert catalog["R10"].fixability.value == "No"
    assert catalog["R12"].fixability.value == "Needs compliance review"
    assert all(catalog[c].fixability.value == "Yes" for c in
               ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R11", "R13"])


@pytest.mark.parametrize("sheet", [config.APPLICATIONS_SHEET, config.CATALOG_SHEET])
def test_missing_sheet_is_fatal(tmp_path, sheet):
    with pytest.raises(DataValidationError, match="missing required sheets"):
        load_workbook(write_workbook(tmp_path, drop_sheet=sheet))


def test_missing_column_is_fatal(tmp_path):
    with pytest.raises(DataValidationError, match="missing required columns"):
        load_workbook(write_workbook(tmp_path, apps=_apps().drop(columns=["whatsapp_opted_in"])))


def test_duplicate_application_id_is_fatal(tmp_path):
    apps = _apps()
    apps.loc[1, "application_id"] = apps.loc[0, "application_id"]
    with pytest.raises(DataValidationError, match="Duplicate application_id"):
        load_workbook(write_workbook(tmp_path, apps=apps))


def test_missing_application_id_is_fatal(tmp_path):
    apps = _apps()
    apps.loc[3, "application_id"] = "   "
    with pytest.raises(DataValidationError, match="Missing application_id"):
        load_workbook(write_workbook(tmp_path, apps=apps))


def test_invalid_and_missing_numbers_are_flagged_not_zeroed(tmp_path):
    apps = _apps()
    apps.loc[0, "expected_monthly_tpv_inr_lakh"] = "about ten"
    apps.loc[1, "days_since_last_activity"] = None
    data = load_workbook(write_workbook(tmp_path, apps=apps))
    clean = data.applications
    assert clean.loc[0, "expected_monthly_tpv_inr_lakh"] is None or pd.isna(clean.loc[0, "expected_monthly_tpv_inr_lakh"])
    assert clean.loc[0, "expected_monthly_tpv_inr_lakh__flag"] == "expected_monthly_tpv_inr_lakh invalid"
    assert clean.loc[1, "days_since_last_activity__flag"] == "days_since_last_activity missing"
    fields = {(i.row_key, i.field) for i in data.issues}
    assert (apps.loc[0, "application_id"], "expected_monthly_tpv_inr_lakh") in fields


def test_unknown_status_and_code_are_warned_not_dropped(tmp_path):
    apps = _apps()
    apps.loc[0, "application_status"] = "On hold"
    apps.loc[1, "rejection_code"] = "R99"
    data = load_workbook(write_workbook(tmp_path, apps=apps))
    messages = " ".join(i.message for i in data.issues)
    assert "Unrecognized status 'On hold'" in messages
    assert "'R99' not in catalog" in messages
    assert len(data.applications) == len(apps)


def test_raw_values_are_preserved(real_data):
    raw = real_data.applications_raw
    assert raw.loc[0, "application_id"] == real_data.applications.loc[0, "application_id"]
    assert pd.isna(raw.loc[raw["application_id"] == "A3005", "rejection_code"]).all()
