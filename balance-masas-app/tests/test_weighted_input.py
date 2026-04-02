from __future__ import annotations

import pytest


def test_weighted_input_matches_daily_module_totals(all_franja_results, closed_franjas):
    result = all_franja_results[closed_franjas[0].id_franja]
    riego_df = result["riego_df"]
    weighted_df = result["weighted_df"]

    first_day = weighted_df.iloc[0]
    raw_first_day = riego_df[riego_df["fecha"] == first_day["fecha"]]

    assert first_day["vol_total_m3"] == pytest.approx(raw_first_day["vol_aplicado_m3"].sum())
    assert first_day["cu_entrada_kg"] == pytest.approx(
        (raw_first_day["vol_aplicado_m3"] * raw_first_day["cu_entrada_gpl"]).sum()
    )
    assert first_day["acid_entrada_gpl"] == pytest.approx(
        (raw_first_day["vol_aplicado_m3"] * raw_first_day["acid_entrada_gpl"]).sum()
        / raw_first_day["vol_aplicado_m3"].sum()
    )


def test_weighted_input_has_valid_phase_labels_and_source_breakdown(all_franja_results):
    for result in all_franja_results.values():
        weighted_df = result["weighted_df"]
        assert set(weighted_df["fase_dominante"].unique()).issubset({"refino", "ils", "mixto", "sin_riego"})
        assert weighted_df["fuente_ils_volumenes"].map(lambda value: isinstance(value, dict)).all()
