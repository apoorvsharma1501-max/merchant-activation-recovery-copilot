"""Shared fixtures and helpers. The catalog always comes from the real workbook."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import config
from core.data_loader import load_workbook


@pytest.fixture(scope="session")
def real_data():
    return load_workbook(config.DEFAULT_WORKBOOK)


@pytest.fixture(scope="session")
def catalog(real_data):
    return real_data.catalog


def make_row(**overrides) -> dict:
    """A clean, in-scope application row as produced by the loader."""
    row = {
        "application_id": "TEST1", "business_type": "Proprietorship", "industry": "Electronics",
        "city": "Pune", "preferred_language": "English", "signup_date": "01 Sep 2026",
        "expected_monthly_tpv_inr_lakh": 10.0, "days_since_last_activity": 5.0,
        "attempts": 1.0, "support_contacts": 0.0, "whatsapp_opted_in": "Yes",
        "whatsapp_opt_in_normalized": "Yes", "whatsapp_allowed": True,
        "step_reached": "KYC docs", "application_status": config.STATUS_STALLED,
        "rejection_code": None, "rejection_message": None,
    }
    row.update(overrides)
    return row


def write_workbook(tmp_path: Path, apps: pd.DataFrame | None = None,
                   catalog: pd.DataFrame | None = None, drop_sheet: str | None = None) -> Path:
    """Write a small test workbook, defaulting to the real P3 sheets."""
    src = config.DEFAULT_WORKBOOK
    if apps is None:
        apps = pd.read_excel(src, sheet_name=config.APPLICATIONS_SHEET, dtype=object).dropna(how="all")
    if catalog is None:
        catalog = pd.read_excel(src, sheet_name=config.CATALOG_SHEET, dtype=object).dropna(how="all")
    path = tmp_path / "test_pack.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        if drop_sheet != config.APPLICATIONS_SHEET:
            apps.to_excel(xw, sheet_name=config.APPLICATIONS_SHEET, index=False)
        if drop_sheet != config.CATALOG_SHEET:
            catalog.to_excel(xw, sheet_name=config.CATALOG_SHEET, index=False)
    return path
