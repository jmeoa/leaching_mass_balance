"""Gestión y resumen de ruteo de soluciones por módulo."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from modules.heap_franja.models import HeapFranjaDataset


def build_irrigation_timeline(dataset: HeapFranjaDataset, franja_id: str) -> pd.DataFrame:
    """Serie de riego diaria por tipo de solución."""
    riego_df = dataset.get_riego_by_franja(franja_id)
    if riego_df.empty:
        return pd.DataFrame()
    timeline = (
        riego_df.groupby(["fecha", "tipo_solucion"], as_index=False)["vol_aplicado_m3"]
        .sum()
        .pivot(index="fecha", columns="tipo_solucion", values="vol_aplicado_m3")
        .fillna(0.0)
        .reset_index()
    )
    for column in ["refino", "ils"]:
        if column not in timeline.columns:
            timeline[column] = 0.0
    timeline["total"] = timeline["refino"] + timeline["ils"]
    return timeline.sort_values("fecha").reset_index(drop=True)


def build_routing_transitions(dataset: HeapFranjaDataset, franja_id: str) -> pd.DataFrame:
    """Cambios de ruteo declarados para la franja."""
    ruteo_df = dataset.get_ruteo_by_franja(franja_id)
    if ruteo_df.empty:
        return pd.DataFrame()
    ordered = ruteo_df.sort_values(["id_modulo", "fecha_inicio"]).reset_index(drop=True)
    ordered["tipo_previo"] = ordered.groupby("id_modulo")["tipo_solucion"].shift(1)
    ordered["fuente_previa"] = ordered.groupby("id_modulo")["fuente_ils"].shift(1)
    transitions = ordered[
        (ordered["tipo_previo"].notna()) &
        (
            (ordered["tipo_previo"] != ordered["tipo_solucion"]) |
            (ordered["fuente_previa"].fillna("") != ordered["fuente_ils"].fillna(""))
        )
    ].copy()
    return transitions.reset_index(drop=True)


def summarize_irrigation_sources(dataset: HeapFranjaDataset, franja_id: str) -> pd.DataFrame:
    """Resume volumen y participación por fuente de riego."""
    riego_df = dataset.get_riego_by_franja(franja_id)
    if riego_df.empty:
        return pd.DataFrame()
    summary = riego_df.copy()
    summary["fuente"] = summary["fuente_ils"].fillna("refino")
    grouped = summary.groupby(["tipo_solucion", "fuente"], as_index=False)["vol_aplicado_m3"].sum()
    total = grouped["vol_aplicado_m3"].sum()
    grouped["participacion_pct"] = grouped["vol_aplicado_m3"] / total * 100.0 if total > 0 else 0.0
    return grouped.sort_values("vol_aplicado_m3", ascending=False).reset_index(drop=True)
