from __future__ import annotations

import pytest

from modules.heap_franja import HeapFranjaDataset


def test_dataset_loads_synthetic_csvs(dataset: HeapFranjaDataset):
    assert len(dataset.ciclos) == 2
    assert len(dataset.franjas) == 14
    assert len(dataset.modulos) == 140
    assert dataset.riego_df["id_franja"].nunique() == 12
    assert dataset.pls_df["id_franja"].nunique() == 12


def test_closed_cycle_has_residual_control_in_range(dataset: HeapFranjaDataset, closed_franjas):
    assert len(closed_franjas) == 6
    recoveries = [franja.recovery_from_residual_pct for franja in closed_franjas]
    assert all(recovery is not None for recovery in recoveries)
    assert min(recoveries) >= 50.0
    assert max(recoveries) <= 75.0


def test_module_lookup_matches_franja_definition(dataset: HeapFranjaDataset, closed_franjas):
    franja = closed_franjas[0]
    modulos_df = dataset.get_modulos_by_franja(franja.id_franja)
    assert len(modulos_df) == franja.n_modulos
    assert modulos_df["tonelaje_estimado_t"].sum() == pytest.approx(franja.tonelaje_t, rel=0.05)
