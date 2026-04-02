from __future__ import annotations

from pathlib import Path

import pytest

from modules.heap_franja import (
    HeapFranjaDataset,
    calculate_acid_balance,
    calculate_copper_balance,
    calculate_leach_ratio,
    calculate_weighted_input,
)


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "synthetic"


@pytest.fixture(scope="session")
def dataset(data_dir: Path) -> HeapFranjaDataset:
    return HeapFranjaDataset.from_csv_dir(data_dir)


@pytest.fixture(scope="session")
def closed_cycle_id() -> str:
    return "PAD-01-C01"


@pytest.fixture(scope="session")
def closed_franjas(dataset: HeapFranjaDataset, closed_cycle_id: str):
    return [
        franja
        for franja in dataset.get_franjas_by_ciclo(closed_cycle_id, operativas_only=True)
        if franja.recovery_from_residual_pct is not None
    ]


@pytest.fixture(scope="session")
def all_franja_results(dataset: HeapFranjaDataset):
    results = {}
    for franja in dataset.franjas.values():
        riego_df = dataset.get_riego_by_franja(franja.id_franja)
        pls_df = dataset.get_pls_by_franja(franja.id_franja)
        modulos_df = dataset.get_modulos_by_franja(franja.id_franja)
        if riego_df.empty or pls_df.empty:
            continue
        weighted_df = calculate_weighted_input(riego_df)
        copper_daily_df, copper_summary = calculate_copper_balance(
            franja,
            riego_df,
            pls_df,
            weighted_input_df=weighted_df,
        )
        acid_daily_df, acid_summary = calculate_acid_balance(
            franja,
            riego_df,
            pls_df,
            weighted_input_df=weighted_df,
            copper_daily_df=copper_daily_df,
        )
        rl_daily_df, rl_summary, module_metrics_df = calculate_leach_ratio(
            franja,
            riego_df,
            modulos_df,
            weighted_input_df=weighted_df,
        )
        results[franja.id_franja] = {
            "franja": franja,
            "riego_df": riego_df,
            "pls_df": pls_df,
            "modulos_df": modulos_df,
            "weighted_df": weighted_df,
            "copper_daily_df": copper_daily_df,
            "copper_summary": copper_summary,
            "acid_daily_df": acid_daily_df,
            "acid_summary": acid_summary,
            "rl_daily_df": rl_daily_df,
            "rl_summary": rl_summary,
            "module_metrics_df": module_metrics_df,
        }
    return results
