from __future__ import annotations

from modules.data_loader import build_synthetic_monthly_input
from modules.electrowinning import calculate_ew_history
from modules.leaching import calculate_leaching_history
from modules.mass_balance import calculate_global_balance
from modules.reports import build_excel_report, build_pdf_report
from modules.solvent_extraction import calculate_sx_history


def test_monthly_stage_modules_generate_consistent_histories():
    monthly_df = build_synthetic_monthly_input()

    leaching_df = calculate_leaching_history(monthly_df)
    sx_df = calculate_sx_history(monthly_df)
    ew_df = calculate_ew_history(monthly_df)

    assert len(leaching_df) == len(monthly_df)
    assert len(sx_df) == len(monthly_df)
    assert len(ew_df) == len(monthly_df)
    assert (leaching_df["recuperacion_lix_pct"] >= 0).all()
    assert (leaching_df["inventario_cu_kg"] >= 0).all()
    assert sx_df["recuperacion_sx_pct"].between(0, 100).all()
    assert (ew_df["acid_generado_ew_kg"] > 0).all()


def test_reports_build_binary_outputs():
    monthly_df = build_synthetic_monthly_input()
    leaching_df = calculate_leaching_history(monthly_df)
    sx_df = calculate_sx_history(monthly_df)
    ew_df = calculate_ew_history(monthly_df)
    global_df, summary = calculate_global_balance(monthly_df)

    excel_bytes = build_excel_report(monthly_df, leaching_df, sx_df, ew_df, global_df)
    pdf_bytes = build_pdf_report(summary, global_df)

    assert excel_bytes[:2] == b"PK"
    assert pdf_bytes[:4] == b"%PDF"
