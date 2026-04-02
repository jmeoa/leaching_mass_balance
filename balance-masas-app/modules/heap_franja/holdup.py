"""
Corrección de holdup por franja.
"""

from __future__ import annotations

import pandas as pd

from modules.heap_franja.config import DEFAULT_CONFIG
from modules.heap_franja.models import Franja, mass_kg_from_solution


PLS_CONCENTRATION_COLUMNS = {
    "cu": "cu_pls_gpl",
    "acid": "acid_pls_gpl",
    "fe_total": "fe_total_pls_gpl",
    "fe2": "fe2_pls_gpl",
    "cl": "cl_pls_gpl",
    "sio2": "sio2_pls_gpl",
    "mn": "mn_pls_gpl",
}


def calculate_design_holdup_volume(
    franja: Franja,
    densidad_solucion_ton_m3: float = DEFAULT_CONFIG.parametros.densidad_solucion_ton_m3,
) -> float:
    """Volumen máximo de solución retenida según humedad residual."""
    return (
        franja.tonelaje_t
        * franja.humedad_residual_pct
        / 100.0
        / densidad_solucion_ton_m3
    )


def build_holdup_profile(
    franja: Franja,
    weighted_input_df: pd.DataFrame,
    pls_df: pd.DataFrame,
    densidad_solucion_ton_m3: float = DEFAULT_CONFIG.parametros.densidad_solucion_ton_m3,
) -> pd.DataFrame:
    """Calcula el perfil diario de inventario de solución retenida."""
    if weighted_input_df.empty or pls_df.empty:
        return pd.DataFrame()

    joined = weighted_input_df.merge(
        pls_df,
        on=["id_franja", "fecha"],
        how="inner",
    ).sort_values("fecha")

    design_holdup_m3 = calculate_design_holdup_volume(
        franja,
        densidad_solucion_ton_m3=densidad_solucion_ton_m3,
    )

    inventory_m3 = 0.0
    previous_concentrations = {name: 0.0 for name in PLS_CONCENTRATION_COLUMNS}
    records: list[dict[str, float]] = []

    for row in joined.to_dict("records"):
        delta_water_m3 = float(row["vol_total_m3"]) - float(row["vol_pls_m3"])
        previous_inventory_m3 = inventory_m3
        inventory_m3 = max(0.0, min(design_holdup_m3, inventory_m3 + delta_water_m3))

        record = {
            "id_franja": row["id_franja"],
            "fecha": row["fecha"],
            "holdup_design_m3": design_holdup_m3,
            "holdup_prev_m3": previous_inventory_m3,
            "holdup_actual_m3": inventory_m3,
            "holdup_delta_m3": inventory_m3 - previous_inventory_m3,
            "holdup_fill_pct": (inventory_m3 / design_holdup_m3 * 100.0)
            if design_holdup_m3 > 0
            else 0.0,
        }

        for species, column in PLS_CONCENTRATION_COLUMNS.items():
            prev_mass = mass_kg_from_solution(previous_inventory_m3, previous_concentrations[species])
            current_mass = mass_kg_from_solution(inventory_m3, float(row[column]))
            record[f"{species}_holdup_prev_kg"] = prev_mass
            record[f"{species}_holdup_actual_kg"] = current_mass
            record[f"{species}_holdup_delta_kg"] = current_mass - prev_mass

        previous_concentrations = {
            species: float(row[column]) for species, column in PLS_CONCENTRATION_COLUMNS.items()
        }
        records.append(record)

    return pd.DataFrame.from_records(records)
