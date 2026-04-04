from __future__ import annotations

import io

import pandas as pd

from modules.data_loader import (
    EXPECTED_MONTHLY_COLUMNS,
    build_synthetic_monthly_input,
    load_monthly_input_file,
    validate_monthly_input,
)


def test_validate_monthly_input_accepts_synthetic_dataset():
    monthly_df = build_synthetic_monthly_input()
    validated, issues = validate_monthly_input(monthly_df)

    assert list(validated.columns) == EXPECTED_MONTHLY_COLUMNS
    assert not [issue for issue in issues if issue["level"] == "error"]
    assert validated["periodo"].is_monotonic_increasing


def test_load_monthly_input_file_parses_csv_bytes():
    monthly_df = build_synthetic_monthly_input().copy()
    monthly_df["periodo"] = monthly_df["periodo"].dt.strftime("%Y-%m")

    buffer = io.StringIO()
    monthly_df.to_csv(buffer, index=False)

    loaded_df, issues = load_monthly_input_file(buffer.getvalue().encode("utf-8"), "monthly_input.csv")

    assert not loaded_df.empty
    assert not [issue for issue in issues if issue["level"] == "error"]
    assert pd.api.types.is_datetime64_any_dtype(loaded_df["periodo"])
