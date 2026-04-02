from __future__ import annotations


def test_acid_balance_closure_exceeds_target(all_franja_results, closed_franjas):
    for franja in closed_franjas:
        summary = all_franja_results[franja.id_franja]["acid_summary"]
        assert summary.acid_consumido_total_kg > 0
        assert summary.acid_cierre_pct > 70.0
        assert summary.ratio_acid_cu_kgkg > 0


def test_acid_balance_components_sum_to_reasonable_total(all_franja_results, closed_franjas):
    for franja in closed_franjas:
        summary = all_franja_results[franja.id_franja]["acid_summary"]
        assigned = (
            summary.acid_por_cu_kg
            + summary.acid_por_fe_kg
            + summary.acid_por_cl_kg
            + summary.acid_por_sio2_kg
            + summary.acid_por_mn_kg
        )
        assert assigned >= summary.acid_consumido_total_kg * 0.7
