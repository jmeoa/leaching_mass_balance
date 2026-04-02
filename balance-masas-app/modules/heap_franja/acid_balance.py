"""
Balance de ácido por franja con descomposición por componente.
"""

from __future__ import annotations

import pandas as pd

from modules.heap_franja.config import DEFAULT_CONFIG, FactoresEstequiometricos
from modules.heap_franja.gangue_proxies import calculate_drx_fe_factor, calculate_gangue_proxies
from modules.heap_franja.holdup import build_holdup_profile
from modules.heap_franja.models import AcidBalanceSummary, Franja
from modules.heap_franja.weighted_input import calculate_weighted_input


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_acid_balance(
    franja: Franja,
    riego_df: pd.DataFrame,
    pls_df: pd.DataFrame,
    weighted_input_df: pd.DataFrame | None = None,
    holdup_df: pd.DataFrame | None = None,
    copper_daily_df: pd.DataFrame | None = None,
    factores: FactoresEstequiometricos = DEFAULT_CONFIG.factores,
) -> tuple[pd.DataFrame, AcidBalanceSummary]:
    """Calcula consumo de ácido y su descomposición por componente."""
    weighted = weighted_input_df if weighted_input_df is not None else calculate_weighted_input(riego_df)
    holdup = holdup_df if holdup_df is not None else build_holdup_profile(franja, weighted, pls_df)
    proxies = calculate_gangue_proxies(franja, weighted, pls_df, holdup)
    copper_daily = copper_daily_df

    daily = proxies.copy()
    if daily.empty:
        return daily, AcidBalanceSummary(
            id_franja=franja.id_franja,
            acid_consumido_total_kg=0.0,
            acid_por_cu_kg=0.0,
            acid_por_fe_kg=0.0,
            acid_por_cl_kg=0.0,
            acid_por_sio2_kg=0.0,
            acid_por_mn_kg=0.0,
            acid_no_asignado_kg=0.0,
            acid_sobre_asignado_kg=0.0,
            acid_cierre_pct=0.0,
            ratio_acid_cu_kgkg=0.0,
            factor_drx_fe=calculate_drx_fe_factor(franja, factores),
        )

    daily["acid_pls_kg"] = daily["vol_pls_m3"] * daily["acid_pls_gpl"]
    daily["acid_consumido_kg"] = (
        daily["acid_entrada_kg"]
        - daily["acid_pls_kg"]
        - daily.get("acid_holdup_delta_kg", 0.0)
    ).clip(lower=0.0)

    if copper_daily is not None and not copper_daily.empty:
        copper_series = (
            copper_daily[["fecha", "cu_extraido_corregido_kg"]]
            .rename(columns={"cu_extraido_corregido_kg": "cu_extraido_balance_kg"})
            .copy()
        )
        daily = daily.merge(copper_series, on="fecha", how="left")
        daily["cu_extraido_corregido_kg"] = daily["cu_extraido_balance_kg"].fillna(
            daily["cu_extraido_corregido_kg"]
        )
        daily = daily.drop(columns=["cu_extraido_balance_kg"])

    daily["cu_extraido_corregido_kg"] = daily["cu_extraido_corregido_kg"].clip(lower=0.0)

    factor_drx_fe = calculate_drx_fe_factor(franja, factores)

    daily["acid_por_cu_kg"] = (
        daily["cu_extraido_corregido_kg"].clip(lower=0.0) * factores.acid_por_cu
    )
    daily["acid_por_fe_kg"] = (
        daily["fe_total_disuelto_kg"].clip(lower=0.0) * factor_drx_fe
    )
    daily["acid_por_cl_kg"] = (
        daily["cl_disuelto_kg"].clip(lower=0.0) * factores.acid_por_cl_atacamita
    )
    daily["acid_por_sio2_kg"] = (
        daily["sio2_disuelto_kg"].clip(lower=0.0) * factores.acid_por_sio2
    )
    daily["acid_por_mn_kg"] = (
        daily["mn_disuelto_kg"].clip(lower=0.0) * factores.acid_por_mn
    )

    daily["acid_asignado_kg"] = (
        daily["acid_por_cu_kg"]
        + daily["acid_por_fe_kg"]
        + daily["acid_por_cl_kg"]
        + daily["acid_por_sio2_kg"]
        + daily["acid_por_mn_kg"]
    )
    daily["acid_no_asignado_kg"] = (
        daily["acid_consumido_kg"] - daily["acid_asignado_kg"]
    ).clip(lower=0.0)
    daily["acid_sobre_asignado_kg"] = (
        daily["acid_asignado_kg"] - daily["acid_consumido_kg"]
    ).clip(lower=0.0)
    daily["acid_cierre_pct"] = 100.0
    has_consumption = daily["acid_consumido_kg"] > 0
    daily.loc[has_consumption, "acid_cierre_pct"] = (
        daily.loc[has_consumption, ["acid_consumido_kg", "acid_asignado_kg"]].min(axis=1)
        / daily.loc[has_consumption, "acid_consumido_kg"]
        * 100.0
    )

    total_acid = float(daily["acid_consumido_kg"].sum())
    total_assigned = float(daily["acid_asignado_kg"].sum())
    summary = AcidBalanceSummary(
        id_franja=franja.id_franja,
        acid_consumido_total_kg=total_acid,
        acid_por_cu_kg=float(daily["acid_por_cu_kg"].sum()),
        acid_por_fe_kg=float(daily["acid_por_fe_kg"].sum()),
        acid_por_cl_kg=float(daily["acid_por_cl_kg"].sum()),
        acid_por_sio2_kg=float(daily["acid_por_sio2_kg"].sum()),
        acid_por_mn_kg=float(daily["acid_por_mn_kg"].sum()),
        acid_no_asignado_kg=max(total_acid - total_assigned, 0.0),
        acid_sobre_asignado_kg=max(total_assigned - total_acid, 0.0),
        acid_cierre_pct=_safe_ratio(min(total_assigned, total_acid), total_acid) * 100.0
        if total_acid > 0
        else 100.0,
        ratio_acid_cu_kgkg=_safe_ratio(
            total_acid,
            float(daily["cu_extraido_corregido_kg"].clip(lower=0.0).sum()),
        ),
        factor_drx_fe=factor_drx_fe,
    )
    return daily.reset_index(drop=True), summary
