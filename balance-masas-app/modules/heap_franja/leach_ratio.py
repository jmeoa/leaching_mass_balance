"""
Razón de lixiviación (RL) y métricas de riego.
"""

from __future__ import annotations

import pandas as pd

from modules.heap_franja.config import DEFAULT_CONFIG
from modules.heap_franja.models import Franja, LeachRatioSummary, ModuleIrrigationMetric
from modules.heap_franja.weighted_input import calculate_weighted_input, classify_solution_phase


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_module_metrics(
    franja: Franja,
    modulos_df: pd.DataFrame,
    riego_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula KPIs de riego por módulo."""
    if modulos_df.empty or riego_df.empty:
        return pd.DataFrame()

    grouped = (
        riego_df.groupby("id_modulo", sort=True)
        .agg(
            id_franja=("id_franja", "first"),
            vol_aplicado_total_m3=("vol_aplicado_m3", "sum"),
            vol_refino_m3=("vol_aplicado_m3", lambda s: float(s[riego_df.loc[s.index, "tipo_solucion"] == "refino"].sum())),
            vol_ils_m3=("vol_aplicado_m3", lambda s: float(s[riego_df.loc[s.index, "tipo_solucion"] == "ils"].sum())),
            dias_refino=("fecha", lambda s: int(s[riego_df.loc[s.index, "tipo_solucion"] == "refino"].nunique())),
            dias_ils=("fecha", lambda s: int(s[riego_df.loc[s.index, "tipo_solucion"] == "ils"].nunique())),
            acid_refino_kg=("acid_entrada_gpl", lambda s: float((riego_df.loc[s.index, "vol_aplicado_m3"] * s)[riego_df.loc[s.index, "tipo_solucion"] == "refino"].sum())),
            acid_ils_kg=("acid_entrada_gpl", lambda s: float((riego_df.loc[s.index, "vol_aplicado_m3"] * s)[riego_df.loc[s.index, "tipo_solucion"] == "ils"].sum())),
        )
        .reset_index()
    )
    grouped = grouped.merge(
        modulos_df[["id_modulo", "tonelaje_estimado_t"]],
        on="id_modulo",
        how="left",
    )

    grouped["tonelaje_estimado_t"] = grouped["tonelaje_estimado_t"].fillna(
        franja.tonelaje_t / max(len(modulos_df), 1)
    )
    grouped["rl_total_m3_t"] = grouped["vol_aplicado_total_m3"] / grouped["tonelaje_estimado_t"]
    grouped["rl_refino_m3_t"] = grouped["vol_refino_m3"] / grouped["tonelaje_estimado_t"]
    grouped["rl_ils_m3_t"] = grouped["vol_ils_m3"] / grouped["tonelaje_estimado_t"]

    total_dias = int(riego_df["fecha"].nunique())
    rl_promedio = float(grouped["rl_total_m3_t"].mean()) if not grouped.empty else 0.0

    records = []
    for row in grouped.to_dict("records"):
        fuentes = tuple(
            sorted(
                {
                    str(value)
                    for value in riego_df.loc[
                        (riego_df["id_modulo"] == row["id_modulo"])
                        & (riego_df["tipo_solucion"] == "ils"),
                        "fuente_ils",
                    ]
                    .dropna()
                    .tolist()
                }
            )
        )
        metric = ModuleIrrigationMetric(
            id_modulo=str(row["id_modulo"]),
            id_franja=str(row["id_franja"]),
            vol_aplicado_total_m3=float(row["vol_aplicado_total_m3"]),
            rl_total_m3_t=float(row["rl_total_m3_t"]),
            rl_refino_m3_t=float(row["rl_refino_m3_t"]),
            rl_ils_m3_t=float(row["rl_ils_m3_t"]),
            dias_refino=int(row["dias_refino"]),
            dias_ils=int(row["dias_ils"]),
            dias_reposo=max(total_dias - int(row["dias_refino"]) - int(row["dias_ils"]), 0),
            acid_refino_kg=float(row["acid_refino_kg"]),
            acid_ils_kg=float(row["acid_ils_kg"]),
            uniformidad_ratio=_safe_ratio(float(row["rl_total_m3_t"]), rl_promedio),
            fuentes_ils=fuentes,
        )
        records.append(metric.to_record())
    return pd.DataFrame.from_records(records).sort_values("id_modulo").reset_index(drop=True)


def calculate_leach_ratio(
    franja: Franja,
    riego_df: pd.DataFrame,
    modulos_df: pd.DataFrame,
    weighted_input_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, LeachRatioSummary, pd.DataFrame]:
    """Calcula la RL diaria/acumulada y el detalle por módulo."""
    weighted = weighted_input_df if weighted_input_df is not None else calculate_weighted_input(riego_df)
    if weighted.empty:
        empty_summary = LeachRatioSummary(
            id_franja=franja.id_franja,
            rl_total_m3_t=0.0,
            rl_refino_m3_t=0.0,
            rl_ils_m3_t=0.0,
            rl_por_area_m=0.0,
            rl_por_altura=0.0,
            tasa_global_m3_m2_dia=0.0,
            rl_por_fuente_m3_t={},
            fase_dominante_global="sin_riego",
        )
        return pd.DataFrame(), empty_summary, pd.DataFrame()

    daily = weighted.copy().sort_values("fecha").reset_index(drop=True)
    daily["rl_total_dia_m3_t"] = daily["vol_total_m3"] / franja.tonelaje_t
    daily["rl_refino_dia_m3_t"] = daily["vol_refino_m3"] / franja.tonelaje_t
    daily["rl_ils_dia_m3_t"] = daily["vol_ils_m3"] / franja.tonelaje_t

    daily["rl_total_acum_m3_t"] = daily["rl_total_dia_m3_t"].cumsum()
    daily["rl_refino_acum_m3_t"] = daily["rl_refino_dia_m3_t"].cumsum()
    daily["rl_ils_acum_m3_t"] = daily["rl_ils_dia_m3_t"].cumsum()

    cumulative_vol = daily["vol_total_m3"].cumsum()
    daily["rl_por_area_acum_m"] = cumulative_vol / franja.area_m2
    daily["rl_por_altura_acum"] = daily["rl_por_area_acum_m"] / franja.altura_m
    daily["tasa_global_diaria_m3_m2_dia"] = daily["vol_total_m3"] / franja.area_m2
    daily["tasa_global_promedio_m3_m2_dia"] = cumulative_vol / franja.area_m2 / (
        pd.RangeIndex(start=1, stop=len(daily) + 1)
    )

    source_totals: dict[str, float] = {}
    for source_dict in daily["fuente_ils_volumenes"].tolist():
        for source, volume in source_dict.items():
            source_totals[source] = source_totals.get(source, 0.0) + float(volume)

    summary = LeachRatioSummary(
        id_franja=franja.id_franja,
        rl_total_m3_t=float(daily["rl_total_acum_m3_t"].iloc[-1]),
        rl_refino_m3_t=float(daily["rl_refino_acum_m3_t"].iloc[-1]),
        rl_ils_m3_t=float(daily["rl_ils_acum_m3_t"].iloc[-1]),
        rl_por_area_m=float(daily["rl_por_area_acum_m"].iloc[-1]),
        rl_por_altura=float(daily["rl_por_altura_acum"].iloc[-1]),
        tasa_global_m3_m2_dia=float(daily["tasa_global_promedio_m3_m2_dia"].iloc[-1]),
        rl_por_fuente_m3_t={
            source: volume / franja.tonelaje_t for source, volume in sorted(source_totals.items())
        },
        fase_dominante_global=classify_solution_phase(
            float(daily["vol_refino_m3"].sum()),
            float(daily["vol_ils_m3"].sum()),
            threshold_pct=DEFAULT_CONFIG.parametros.umbral_dominancia_pct,
        ),
    )

    module_metrics = calculate_module_metrics(franja, modulos_df, riego_df)
    return daily, summary, module_metrics
