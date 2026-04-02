from __future__ import annotations


def test_holdup_never_exceeds_design_capacity(all_franja_results, closed_franjas):
    result = all_franja_results[closed_franjas[0].id_franja]
    copper_daily_df = result["copper_daily_df"]

    assert (copper_daily_df["holdup_actual_m3"] >= 0).all()
    assert (copper_daily_df["holdup_fill_pct"] <= 100.0 + 1e-9).all()
