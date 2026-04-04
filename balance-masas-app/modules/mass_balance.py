"""Integración mensual del balance global Cu/H2SO4 para LIX-SX-EW."""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from modules.electrowinning import calculate_ew_history
from modules.leaching import calculate_leaching_history
from modules.solvent_extraction import calculate_sx_history


def calculate_global_balance(monthly_input_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Calcula balance global mensual y resumen consolidado."""
    leaching_df = calculate_leaching_history(monthly_input_df)
    sx_df = calculate_sx_history(monthly_input_df)
    ew_df = calculate_ew_history(monthly_input_df)

    merged = leaching_df.merge(sx_df, on="periodo", how="left").merge(ew_df, on="periodo", how="left")
    merged["inventory_delta_kg"] = merged["inventario_cu_kg"].diff().fillna(merged["inventario_cu_kg"])
    merged["solution_delta_kg"] = merged["cu_transferido_kg"] - merged["cu_depositado_kg"]
    merged["cu_perdidas_kg"] = (
        merged["cu_alimentado_kg"] - merged["cu_depositado_kg"] - merged["inventory_delta_kg"] - merged["solution_delta_kg"]
    )
    merged["recuperacion_global_pct"] = (
        merged["cu_depositado_kg"] / merged["cu_alimentado_kg"] * 100.0
    ).where(merged["cu_alimentado_kg"] > 0, 0.0)

    merged["acid_entrada_kg"] = (
        monthly_input_df["acid_makeup_ton"].to_numpy() * 1000.0
        + merged["acid_generado_ew_kg"]
        + merged["acid_generado_extraccion_kg"]
    )
    merged["acid_salida_kg"] = merged["acid_consumido_lix_kg"] + merged["acid_consumido_stripping_kg"]
    merged["acid_neto_kg"] = merged["acid_entrada_kg"] - merged["acid_salida_kg"]
    merged["consumo_neto_acido_kgkg"] = (
        monthly_input_df["acid_makeup_ton"].to_numpy() * 1000.0 / merged["cu_depositado_kg"]
    ).where(merged["cu_depositado_kg"] > 0, 0.0)

    summary = {
        "cu_alimentado_total_t": float(merged["cu_alimentado_kg"].sum() / 1000.0),
        "cu_catodos_total_t": float(merged["cu_depositado_kg"].sum() / 1000.0),
        "recuperacion_global_pct": float(
            (merged["cu_depositado_kg"].sum() / merged["cu_alimentado_kg"].sum() * 100.0)
            if merged["cu_alimentado_kg"].sum() > 0
            else 0.0
        ),
        "acid_makeup_total_t": float(monthly_input_df["acid_makeup_ton"].sum()),
        "acid_neto_total_t": float(merged["acid_neto_kg"].sum() / 1000.0),
    }
    return merged, summary
