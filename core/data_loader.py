"""Load and validate the P3 sheets. Raw values are preserved; a cleaned copy is used for logic."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

import config
from schemas.labels import Fixability


class DataValidationError(Exception):
    """Fatal problem: the workbook cannot be processed safely."""


@dataclass(frozen=True)
class DataIssue:
    severity: str  # "ERROR" | "WARNING"
    sheet: str
    row_key: str | None
    field: str | None
    message: str


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    reviewer_reason: str | None
    plain_language_meaning: str | None
    fixable_raw: str | None
    fixability: Fixability
    standard_fix: str | None
    typical_days_to_fix: float | None  # reference only, never promised to merchants


@dataclass
class LoadedData:
    source_file: str
    applications_raw: pd.DataFrame
    applications: pd.DataFrame
    catalog: dict[str, CatalogEntry]
    issues: list[DataIssue] = field(default_factory=list)


_FIXABILITY_MAP = {
    "yes": Fixability.YES,
    "no": Fixability.NO,
    "needs compliance review": Fixability.NEEDS_COMPLIANCE_REVIEW,
}


def normalize_text(value) -> str | None:
    """Strip whitespace; return None for empty cells and missing-value tokens."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    text = str(value).strip()
    if text.lower() in config.MISSING_TOKENS:
        return None
    return text


def parse_number(value) -> tuple[float | None, bool]:
    """Return (number, is_invalid). Missing -> (None, False); unparseable -> (None, True)."""
    text = normalize_text(value)
    if text is None:
        return None, False
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return None, True
    if math.isnan(number) or math.isinf(number):
        return None, True
    return number, False


def _require_columns(df: pd.DataFrame, required: list[str], sheet: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataValidationError(f"Sheet '{sheet}' is missing required columns: {missing}")


def _read_sheet(xls: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    df = pd.read_excel(xls, sheet_name=sheet, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    # The workbook has formatted-but-empty rows; drop rows with no values at all.
    return df.dropna(how="all").reset_index(drop=True)


def _clean_applications(raw: pd.DataFrame, issues: list[DataIssue]) -> pd.DataFrame:
    sheet = config.APPLICATIONS_SHEET
    clean = pd.DataFrame(index=raw.index)

    def _obj(values) -> pd.Series:
        # object dtype keeps None as None (pandas 3 would otherwise infer str/NaN)
        return pd.Series(list(values), index=raw.index, dtype=object)

    for col in config.APPLICATION_COLUMNS:
        if col in config.APPLICATION_NUMERIC_COLUMNS:
            continue
        clean[col] = _obj(normalize_text(v) for v in raw[col])

    ids = clean["application_id"]
    if ids.isna().any():
        rows = [int(i) + 2 for i in ids[ids.isna()].index]  # +2: header row and 1-based
        raise DataValidationError(f"Missing application_id in Excel rows {rows}")
    dupes = sorted(ids[ids.duplicated(keep=False)].unique())
    if dupes:
        raise DataValidationError(f"Duplicate application_id values: {dupes}")

    for col in config.APPLICATION_NUMERIC_COLUMNS:
        values, flags = [], []
        for app_id, raw_value in zip(ids, raw[col]):
            number, invalid = parse_number(raw_value)
            values.append(number)
            if invalid:
                flags.append(f"{col} invalid")
                issues.append(DataIssue("WARNING", sheet, app_id, col,
                                        f"Unparseable value {raw_value!r}; left empty, not set to 0"))
            elif number is None:
                flags.append(f"{col} missing")
                issues.append(DataIssue("WARNING", sheet, app_id, col, "Missing value"))
            elif number < 0:
                flags.append(f"{col} negative")
                issues.append(DataIssue("WARNING", sheet, app_id, col, f"Negative value {number}"))
            else:
                flags.append(None)
        clean[col] = _obj(values)
        clean[f"{col}__flag"] = _obj(flags)

    clean["rejection_code"] = _obj(c.upper() if c else None for c in clean["rejection_code"])

    def _wa(value: str | None) -> str:
        if value is None:
            return "Missing"
        low = value.lower()
        if low in config.WHATSAPP_AFFIRMATIVE:
            return "Yes"
        if low in {"no", "n", "false"}:
            return "No"
        return "Unrecognized"

    clean["whatsapp_opt_in_normalized"] = _obj(_wa(v) for v in clean["whatsapp_opted_in"])
    clean["whatsapp_allowed"] = _obj(v == "Yes" for v in clean["whatsapp_opt_in_normalized"])
    for app_id, wa in zip(ids, clean["whatsapp_opt_in_normalized"]):
        if wa in {"Missing", "Unrecognized"}:
            issues.append(DataIssue("WARNING", sheet, app_id, "whatsapp_opted_in",
                                    f"Opt-in {wa.lower()}; WhatsApp not permitted"))

    for app_id, status in zip(ids, clean["application_status"]):
        if status not in config.KNOWN_STATUSES:
            issues.append(DataIssue("WARNING", sheet, app_id, "application_status",
                                    f"Unrecognized status {status!r}; requires human review"))

    for app_id, lang in zip(ids, clean["preferred_language"]):
        if lang not in config.SUPPORTED_LANGUAGES:
            issues.append(DataIssue("WARNING", sheet, app_id, "preferred_language",
                                    f"Unsupported or missing language {lang!r}"))

    # Cross-field check: inactivity cannot be longer than the account has existed at the snapshot.
    # Flag only; the values are kept as given.
    consistency = []
    for app_id, signup, days in zip(ids, clean["signup_date"], clean["days_since_last_activity"]):
        flag = None
        if signup:
            try:
                age = (config.SNAPSHOT_DATE - datetime.strptime(signup, config.SIGNUP_DATE_FORMAT).date()).days
            except ValueError:
                flag = "signup_date unparseable"
                issues.append(DataIssue("WARNING", sheet, app_id, "signup_date", f"Unparseable date {signup!r}"))
            else:
                if days is not None and days > age:
                    flag = f"inactivity ({days:g} d) exceeds days since signup ({age} d)"
                    issues.append(DataIssue("WARNING", sheet, app_id, "days_since_last_activity",
                                            f"{flag} at snapshot {config.SNAPSHOT_DATE:%d %b %Y}; "
                                            "recency-based priority is unreliable for this row"))
        consistency.append(flag)
    clean["activity_consistency_flag"] = _obj(consistency)
    return clean


def _build_catalog(raw: pd.DataFrame, issues: list[DataIssue]) -> dict[str, CatalogEntry]:
    sheet = config.CATALOG_SHEET
    catalog: dict[str, CatalogEntry] = {}
    for _, row in raw.iterrows():
        code = normalize_text(row["code"])
        if code is None:
            issues.append(DataIssue("WARNING", sheet, None, "code", "Catalog row without a code ignored"))
            continue
        code = code.upper()
        if code in catalog:
            raise DataValidationError(f"Duplicate catalog code {code}")
        fixable_raw = normalize_text(row["fixable"])
        fixability = _FIXABILITY_MAP.get((fixable_raw or "").lower(), Fixability.UNKNOWN)
        if fixability is Fixability.UNKNOWN:
            issues.append(DataIssue("WARNING", sheet, code, "fixable",
                                    f"Unrecognized fixable value {fixable_raw!r}; treated as Unknown"))
        days, invalid = parse_number(row["typical_days_to_fix"])
        if invalid:
            issues.append(DataIssue("WARNING", sheet, code, "typical_days_to_fix", "Unparseable value"))
        catalog[code] = CatalogEntry(
            code=code,
            reviewer_reason=normalize_text(row["reviewer_reason"]),
            plain_language_meaning=normalize_text(row["plain_language_meaning"]),
            fixable_raw=fixable_raw,
            fixability=fixability,
            standard_fix=normalize_text(row["standard_fix"]),
            typical_days_to_fix=days,
        )
    if config.INACTIVITY_CODE not in catalog:
        issues.append(DataIssue("ERROR", sheet, config.INACTIVITY_CODE, "code",
                                "Inactivity code missing from catalog; inactivity cases go to human review"))
    return catalog


def load_workbook(path: str | Path = config.DEFAULT_WORKBOOK) -> LoadedData:
    path = Path(path)
    if not path.exists():
        raise DataValidationError(f"Workbook not found: {path}")
    with pd.ExcelFile(path, engine="openpyxl") as xls:
        missing = [s for s in (config.APPLICATIONS_SHEET, config.CATALOG_SHEET) if s not in xls.sheet_names]
        if missing:
            raise DataValidationError(f"Workbook is missing required sheets: {missing}")
        apps_raw = _read_sheet(xls, config.APPLICATIONS_SHEET)
        cat_raw = _read_sheet(xls, config.CATALOG_SHEET)

    _require_columns(apps_raw, config.APPLICATION_COLUMNS, config.APPLICATIONS_SHEET)
    _require_columns(cat_raw, config.CATALOG_COLUMNS, config.CATALOG_SHEET)

    issues: list[DataIssue] = []
    catalog = _build_catalog(cat_raw, issues)
    apps = _clean_applications(apps_raw, issues)

    for app_id, code in zip(apps["application_id"], apps["rejection_code"]):
        if code and code not in catalog:
            issues.append(DataIssue("WARNING", config.APPLICATIONS_SHEET, app_id, "rejection_code",
                                    f"Code {code!r} not in catalog; requires human review"))

    return LoadedData(path.name, apps_raw, apps, catalog, issues)
