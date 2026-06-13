"""
data_loader.py — Load, validate, and align budget and actuals files.

WHAT IT DOES (in finance terms):
  This is the "intake" step — like an accountant checking that the files
  finance sent you are actually usable before you start any analysis.
  It answers three questions:
    1. Do the files have the columns we expect?
    2. Which months are "closed" (i.e., actuals exist for them)?
    3. Does the budget file cover those same months?

WHY IT MATTERS:
  If you skip validation and load a malformed file, the variance engine
  will silently produce wrong numbers — or crash halfway through with a
  cryptic error that's impossible to debug.  Validating at the front door
  means errors surface immediately with a clear message, not after 30
  seconds of computation.

INTERVIEW ANGLE:
  "What happens if someone uploads a file with the wrong column names?"
  Answer: load_data() raises a ValueError with the exact column that's
  missing, before any analysis runs.  The tool never silently produces
  wrong output.
"""

import pandas as pd
import os
from src.config import REQUIRED_COLUMNS


# ── Public entry point ────────────────────────────────────────────────────────

def load_data(budget_path: str, actuals_path: str, drivers_path: str = None):
    """
    Load and validate all input files.  Returns a dict with four keys:
      "budget"        — full-year budget DataFrame (all 12 months)
      "actuals"       — actuals DataFrame (closed months only)
      "drivers"       — driver notes DataFrame (or empty DataFrame if not provided)
      "closed_months" — sorted list of months that exist in actuals, e.g. ["2026-01", ..., "2026-06"]
      "budget_closed" — budget DataFrame sliced to only the closed months

    Raises ValueError with a clear message if anything is wrong.
    """
    budget          = _load_file(budget_path,  label="Budget")
    actuals         = _load_file(actuals_path, label="Actuals")
    drivers         = _load_drivers(drivers_path)

    _validate_columns(budget,  label="Budget")
    _validate_columns(actuals, label="Actuals")
    _validate_amounts(budget,  label="Budget")
    _validate_amounts(actuals, label="Actuals")
    _validate_months(budget,   label="Budget")
    _validate_months(actuals,  label="Actuals")

    closed_months   = _detect_closed_months(actuals)
    budget_closed   = _slice_budget_to_closed(budget, closed_months, budget_path)

    _validate_coverage(budget_closed, actuals)

    return {
        "budget":        budget,
        "actuals":       actuals,
        "drivers":       drivers,
        "closed_months": closed_months,
        "budget_closed": budget_closed,
    }


# ── Internal helpers (each does ONE thing) ────────────────────────────────────

def _load_file(path: str, label: str) -> pd.DataFrame:
    """
    Read an Excel or CSV file.  Raises a clear error if the file is missing
    or the extension is not supported.

    WHY: A stranger using this tool might mistype the path or upload a PDF
    by accident.  We catch that here with a message they can act on.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{label} file not found: '{path}'\n"
            f"Check that the file path is correct and the file is in the right folder."
        )

    ext = os.path.splitext(path)[1].lower()

    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif ext == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(
            f"{label} file must be .xlsx, .xls, or .csv — got '{ext}'\n"
            f"Save your file as Excel or CSV and try again."
        )

    if df.empty:
        raise ValueError(
            f"{label} file loaded but contains no data rows.\n"
            f"Check that the file is not blank and has a header row."
        )

    # Strip leading/trailing whitespace from column names and string columns.
    # WHY: Excel files often have invisible spaces in headers ("Amount ")
    # that cause column-not-found errors that are maddening to debug.
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    return df


def _load_drivers(path: str | None) -> pd.DataFrame:
    """
    Load the drivers file if provided.  Returns an empty DataFrame if not —
    the tool works without it, but AI commentary will note missing drivers.
    """
    if path is None or not os.path.exists(path):
        return pd.DataFrame(columns=["Month", "Department", "Line Item", "Driver Note"])

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df


def _validate_columns(df: pd.DataFrame, label: str):
    """
    Check that all five required columns are present.

    WHY: The variance engine merges on ["Month", "Department", "Line Item",
    "Category"] and sums "Amount".  If any of these is missing (or misspelled
    as "Amounts" or "Dept"), the merge will fail silently or crash.
    We catch it here with a clear message.

    INTERVIEW ANGLE: "How do you make the tool robust to user error?"
    Answer: check for required columns before any computation and name
    exactly which column is missing so the user can fix it in 10 seconds.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"{label} file is missing required column(s): {missing}\n"
            f"Your file has these columns: {list(df.columns)}\n"
            f"Required columns are: {REQUIRED_COLUMNS}"
        )


def _validate_amounts(df: pd.DataFrame, label: str):
    """
    Check that the Amount column is numeric (int or float).

    WHY: Excel files with currency formatting sometimes export Amount as
    "$1,200,000" — a string.  pd.sum() on a string column returns "0" with
    no error, silently breaking every variance calculation downstream.
    """
    if not pd.api.types.is_numeric_dtype(df["Amount"]):
        sample = df["Amount"].head(3).tolist()
        raise ValueError(
            f"{label} 'Amount' column must be numeric (e.g. 820000), "
            f"but found values like: {sample}\n"
            f"Remove currency symbols, commas, or text from the Amount column."
        )

    null_count = df["Amount"].isna().sum()
    if null_count > 0:
        raise ValueError(
            f"{label} 'Amount' column has {null_count} blank cell(s).\n"
            f"Fill or remove blank rows before uploading."
        )


def _validate_months(df: pd.DataFrame, label: str):
    """
    Check that Month values follow YYYY-MM format (e.g. "2026-01").

    WHY: If Month is a date object ("2026-01-01") or a different string
    format ("Jan-26"), the merge keys won't match and you'll get zero rows —
    the tool would silently say everything is fine with no variances.
    """
    sample_month = str(df["Month"].iloc[0])
    if len(sample_month) != 7 or sample_month[4] != "-":
        raise ValueError(
            f"{label} 'Month' column must use YYYY-MM format (e.g. '2026-01').\n"
            f"Found: '{sample_month}'\n"
            f"Reformat your Month column before uploading."
        )


def _detect_closed_months(actuals: pd.DataFrame) -> list:
    """
    Return a sorted list of months that exist in the actuals file.
    These are the only months where we have real data to compare against.

    WHY: Budget covers 12 months.  Actuals only covers months that have
    closed (accounting has finalized the numbers).  Comparing actuals vs
    budget for a month that hasn't happened yet would be nonsense — you'd
    show a 100% unfavorable variance on every future line item.

    INTERVIEW ANGLE: "How do you handle a partial year?"
    Answer: detect closed months from actuals and use that as the filter.
    The analysis automatically covers exactly the months that matter,
    regardless of when in the year the tool is run.
    """
    closed = sorted(actuals["Month"].unique().tolist())
    return closed


def _slice_budget_to_closed(budget: pd.DataFrame, closed_months: list, path: str) -> pd.DataFrame:
    """
    Filter the budget DataFrame to only the rows matching closed months.

    WHY: The variance engine merges budget and actuals.  If budget has 144
    rows (12 months × 12 line items) but actuals only has 72 rows (6 months),
    an outer join would produce 72 rows with null actuals — impossible to
    handle cleanly.  We trim budget first so both sides are the same shape.
    """
    budget_closed = budget[budget["Month"].isin(closed_months)].copy()

    if budget_closed.empty:
        raise ValueError(
            f"Budget file has no rows matching the closed months from actuals: {closed_months}\n"
            f"Budget months found: {sorted(budget['Month'].unique().tolist())}\n"
            f"Check that both files use the same YYYY-MM month format."
        )

    return budget_closed


def _validate_coverage(budget_closed: pd.DataFrame, actuals: pd.DataFrame):
    """
    Warn if actuals has months or line items that budget doesn't cover.

    WHY: A missing budget row means the merge will drop that actual row,
    producing an incomplete variance report.  Better to flag this here
    than to silently undercount variances.
    """
    budget_months  = set(budget_closed["Month"].unique())
    actuals_months = set(actuals["Month"].unique())
    uncovered = actuals_months - budget_months

    if uncovered:
        # Not a hard error — partial coverage is valid — but we warn.
        print(
            f"[DATA LOADER WARNING] Actuals contain month(s) with no matching "
            f"budget rows: {sorted(uncovered)}.  Those rows will be excluded "
            f"from the variance analysis."
        )

    budget_keys  = set(zip(budget_closed["Department"], budget_closed["Line Item"]))
    actuals_keys = set(zip(actuals["Department"],       actuals["Line Item"]))
    missing_keys = actuals_keys - budget_keys

    if missing_keys:
        print(
            f"[DATA LOADER WARNING] {len(missing_keys)} Department + Line Item "
            f"combination(s) exist in actuals but not in budget: {missing_keys}.\n"
            f"These rows will be excluded from variance analysis."
        )
