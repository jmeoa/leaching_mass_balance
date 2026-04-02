from __future__ import annotations

import pytest


def test_leach_ratio_summary_is_consistent(all_franja_results, closed_franjas):
    for franja in closed_franjas:
        summary = all_franja_results[franja.id_franja]["rl_summary"]
        assert summary.rl_total_m3_t > 0
        assert summary.rl_refino_m3_t + summary.rl_ils_m3_t == pytest.approx(summary.rl_total_m3_t)
        assert summary.rl_por_altura > 0


def test_module_metrics_cover_all_modules(all_franja_results, closed_franjas):
    franja = closed_franjas[0]
    result = all_franja_results[franja.id_franja]
    module_metrics_df = result["module_metrics_df"]
    modulos_df = result["modulos_df"]

    assert len(module_metrics_df) == len(modulos_df)
    assert (module_metrics_df["uniformidad_ratio"] > 0).all()
    assert (module_metrics_df["dias_refino"] + module_metrics_df["dias_ils"] <= result["weighted_df"]["fecha"].nunique()).all()
