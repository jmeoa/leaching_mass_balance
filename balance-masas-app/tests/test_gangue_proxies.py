from __future__ import annotations


def test_gangue_proxies_capture_species_dissolution(all_franja_results, closed_franjas):
    result = all_franja_results[closed_franjas[0].id_franja]
    acid_daily_df = result["acid_daily_df"]

    assert "fe_total_disuelto_kg" in acid_daily_df.columns
    assert "cl_disuelto_kg" in acid_daily_df.columns
    assert acid_daily_df["fe_factor_drx"].iloc[0] >= 2.0
    assert acid_daily_df["fe_factor_drx"].iloc[0] <= 2.63
