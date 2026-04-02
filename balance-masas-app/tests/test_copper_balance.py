from __future__ import annotations


def test_closed_cycle_recoveries_stay_in_expected_band(all_franja_results, closed_franjas):
    recoveries = []
    for franja in closed_franjas:
        summary = all_franja_results[franja.id_franja]["copper_summary"]
        recoveries.append(summary.recovery_pct)
        assert 50.0 <= summary.recovery_pct <= 75.0

    assert min(recoveries) >= 50.0
    assert max(recoveries) <= 75.0


def test_copper_balance_exposes_direct_and_reconciled_views(all_franja_results, closed_franjas):
    summary = all_franja_results[closed_franjas[0].id_franja]["copper_summary"]
    assert summary.recovery_direct_pct > 0
    assert summary.recovery_residual_pct is not None
    assert summary.recovery_pct != summary.recovery_direct_pct
    assert summary.cu_extraido_directo_kg > 0
