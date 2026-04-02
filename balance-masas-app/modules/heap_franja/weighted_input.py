"""
Cálculo de entrada ponderada desde módulos hacia la franja.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from modules.heap_franja.models import (
    EntradaPonderada,
    concentration_gpl_from_mass,
    mass_kg_from_solution,
)


INPUT_CONCENTRATION_COLUMNS = {
    "cu": "cu_entrada_gpl",
    "acid": "acid_entrada_gpl",
    "fe_total": "fe_total_entrada_gpl",
    "fe2": "fe2_entrada_gpl",
    "cl": "cl_entrada_gpl",
    "sio2": "sio2_entrada_gpl",
    "mn": "mn_entrada_gpl",
}


def classify_solution_phase(
    vol_refino_m3: float,
    vol_ils_m3: float,
    threshold_pct: float = 70.0,
) -> str:
    """Clasifica el día según la solución dominante."""
    vol_total = vol_refino_m3 + vol_ils_m3
    if vol_total <= 0:
        return "sin_riego"
    if vol_refino_m3 / vol_total * 100 >= threshold_pct:
        return "refino"
    if vol_ils_m3 / vol_total * 100 >= threshold_pct:
        return "ils"
    return "mixto"


def calculate_weighted_input_for_day(
    id_franja: str,
    fecha: pd.Timestamp,
    riego_dia_df: pd.DataFrame,
    threshold_pct: float = 70.0,
) -> EntradaPonderada:
    """Calcula la entrada ponderada diaria de una franja."""
    ordered = riego_dia_df.copy().sort_values("id_modulo")
    vol_total = float(ordered["vol_aplicado_m3"].sum())
    vol_refino = float(
        ordered.loc[ordered["tipo_solucion"] == "refino", "vol_aplicado_m3"].sum()
    )
    vol_ils = float(
        ordered.loc[ordered["tipo_solucion"] == "ils", "vol_aplicado_m3"].sum()
    )

    masses: dict[str, float] = {}
    concentrations: dict[str, float] = {}
    for key, column in INPUT_CONCENTRATION_COLUMNS.items():
        mass = float((ordered["vol_aplicado_m3"] * ordered[column]).sum())
        masses[key] = mass
        concentrations[key] = concentration_gpl_from_mass(mass, vol_total)

    ils_source_volumes = (
        ordered.loc[ordered["tipo_solucion"] == "ils", ["fuente_ils", "vol_aplicado_m3"]]
        .dropna(subset=["fuente_ils"])
        .groupby("fuente_ils")["vol_aplicado_m3"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    return EntradaPonderada(
        id_franja=id_franja,
        fecha=fecha.date(),
        vol_total_m3=vol_total,
        vol_refino_m3=vol_refino,
        vol_ils_m3=vol_ils,
        n_modulos_regados=int(ordered["id_modulo"].nunique()),
        n_modulos_refino=int(
            ordered.loc[ordered["tipo_solucion"] == "refino", "id_modulo"].nunique()
        ),
        n_modulos_ils=int(
            ordered.loc[ordered["tipo_solucion"] == "ils", "id_modulo"].nunique()
        ),
        cu_entrada_kg=masses["cu"],
        acid_entrada_kg=masses["acid"],
        fe_total_entrada_kg=masses["fe_total"],
        fe2_entrada_kg=masses["fe2"],
        cl_entrada_kg=masses["cl"],
        sio2_entrada_kg=masses["sio2"],
        mn_entrada_kg=masses["mn"],
        cu_entrada_gpl=concentrations["cu"],
        acid_entrada_gpl=concentrations["acid"],
        fe_total_entrada_gpl=concentrations["fe_total"],
        fe2_entrada_gpl=concentrations["fe2"],
        fe3_entrada_gpl=max(concentrations["fe_total"] - concentrations["fe2"], 0.0),
        cl_entrada_gpl=concentrations["cl"],
        sio2_entrada_gpl=concentrations["sio2"],
        mn_entrada_gpl=concentrations["mn"],
        fuente_ils_volumenes={str(key): float(value) for key, value in ils_source_volumes.items()},
        fase_dominante=classify_solution_phase(vol_refino, vol_ils, threshold_pct),
    )


def calculate_weighted_input(
    riego_df: pd.DataFrame,
    threshold_pct: float = 70.0,
) -> pd.DataFrame:
    """Calcula la serie diaria de entrada ponderada para una o más franjas."""
    if riego_df.empty:
        return pd.DataFrame()

    normalized = riego_df.copy()
    normalized["fecha"] = pd.to_datetime(normalized["fecha"]).dt.normalize()

    records: list[dict[str, Any]] = []
    grouped = normalized.groupby(["id_franja", "fecha"], sort=True)
    for (id_franja, fecha), group in grouped:
        weighted = calculate_weighted_input_for_day(
            id_franja=id_franja,
            fecha=pd.Timestamp(fecha),
            riego_dia_df=group,
            threshold_pct=threshold_pct,
        )
        records.append(weighted.to_record())

    result = pd.DataFrame.from_records(records).sort_values(["id_franja", "fecha"])
    return result.reset_index(drop=True)


def build_weighted_input_for_franja(
    riego_df: pd.DataFrame,
    id_franja: str,
    threshold_pct: float = 70.0,
) -> pd.DataFrame:
    """Conveniencia para una sola franja."""
    filtered = riego_df[riego_df["id_franja"] == id_franja].copy()
    return calculate_weighted_input(filtered, threshold_pct=threshold_pct)


def calculate_source_input_masses(riego_df: pd.DataFrame) -> pd.DataFrame:
    """Desglosa masas y volúmenes de entrada por tipo/fuente de solución."""
    if riego_df.empty:
        return pd.DataFrame()

    normalized = riego_df.copy()
    normalized["fecha"] = pd.to_datetime(normalized["fecha"]).dt.normalize()
    normalized["fuente"] = normalized["fuente_ils"].fillna("refino")

    records = []
    grouped = normalized.groupby(["id_franja", "fecha", "tipo_solucion", "fuente"], sort=True)
    for (id_franja, fecha, tipo, fuente), group in grouped:
        records.append(
            {
                "id_franja": id_franja,
                "fecha": pd.Timestamp(fecha),
                "tipo_solucion": tipo,
                "fuente": fuente,
                "vol_total_m3": float(group["vol_aplicado_m3"].sum()),
                "cu_entrada_kg": float(
                    (group["vol_aplicado_m3"] * group["cu_entrada_gpl"]).sum()
                ),
                "acid_entrada_kg": float(
                    (group["vol_aplicado_m3"] * group["acid_entrada_gpl"]).sum()
                ),
            }
        )
    return pd.DataFrame.from_records(records).sort_values(
        ["id_franja", "fecha", "tipo_solucion", "fuente"]
    )
