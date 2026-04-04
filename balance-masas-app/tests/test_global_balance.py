from __future__ import annotations

from modules.data_loader import build_synthetic_monthly_input
from modules.mass_balance import calculate_global_balance


def test_global_balance_builds_from_synthetic_monthly_input():
    monthly_df = build_synthetic_monthly_input()
    global_df, summary = calculate_global_balance(monthly_df)

    assert not global_df.empty
    assert summary["cu_alimentado_total_t"] > 0
    assert summary["cu_catodos_total_t"] > 0
    assert 0 < summary["recuperacion_global_pct"] < 100
    assert "consumo_neto_acido_kgkg" in global_df.columns
