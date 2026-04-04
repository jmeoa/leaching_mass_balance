"""Agregaciones franja → ciclo → pad."""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from modules.heap_franja.models import HeapFranjaDataset


def aggregate_cycle_results(dataset: HeapFranjaDataset, analysis_by_franja: Dict[str, Dict[str, object]], cycle_id: str) -> pd.DataFrame:
    """Resume un ciclo a partir de análisis por franja."""
    rows = []
    for franja in dataset.get_franjas_by_ciclo(cycle_id, operativas_only=True):
        analysis = analysis_by_franja.get(franja.id_franja)
        if not analysis:
            continue
        copper = analysis["copper_summary"]
        acid = analysis["acid_summary"]
        rl = analysis["rl_summary"]
        rows.append(
            {
                "id_franja": franja.id_franja,
                "numero_franja": franja.numero_franja,
                "recovery_pct": float(copper.recovery_pct),
                "acid_cierre_pct": float(acid.acid_cierre_pct),
                "acid_ratio_kgkg": float(acid.ratio_acid_cu_kgkg),
                "cu_extraido_t": float(copper.cu_extraido_reconciliado_kg) / 1000.0,
                "rl_total_m3_t": float(rl.rl_total_m3_t),
                "fase_dominante": rl.fase_dominante_global,
            }
        )
    return pd.DataFrame(rows).sort_values("numero_franja").reset_index(drop=True)


def aggregate_pad_results(dataset: HeapFranjaDataset, analysis_by_franja: Dict[str, Dict[str, object]]) -> pd.DataFrame:
    """Resume un pad consolidando todos sus ciclos."""
    rows = []
    for ciclo in dataset.get_ciclos():
        cycle_df = aggregate_cycle_results(dataset, analysis_by_franja, ciclo.id_ciclo)
        if cycle_df.empty:
            continue
        rows.append(
            {
                "id_pad": ciclo.id_pad,
                "id_ciclo": ciclo.id_ciclo,
                "recovery_promedio_pct": float(cycle_df["recovery_pct"].mean()),
                "acid_cierre_promedio_pct": float(cycle_df["acid_cierre_pct"].mean()),
                "cu_extraido_t": float(cycle_df["cu_extraido_t"].sum()),
                "rl_promedio_m3_t": float(cycle_df["rl_total_m3_t"].mean()),
            }
        )
    return pd.DataFrame(rows)
