"""
Proxys de disolución de ganga y factores mineralógicos.
"""

from __future__ import annotations

import pandas as pd

from modules.heap_franja.config import DEFAULT_CONFIG, FactoresEstequiometricos
from modules.heap_franja.models import Franja, mass_kg_from_solution


def calculate_drx_fe_factor(
    franja: Franja,
    factores: FactoresEstequiometricos = DEFAULT_CONFIG.factores,
) -> float:
    """Factor ponderado de ácido por Fe usando goethita y clorita."""
    reactive_fraction = franja.pct_goethita + franja.pct_clorita
    if reactive_fraction <= 0:
        return (factores.acid_por_fe_goethita + factores.acid_por_fe_clorita) / 2.0
    return (
        franja.pct_goethita * factores.acid_por_fe_goethita
        + franja.pct_clorita * factores.acid_por_fe_clorita
    ) / reactive_fraction


def calculate_gangue_proxies(
    franja: Franja,
    weighted_input_df: pd.DataFrame,
    pls_df: pd.DataFrame,
    holdup_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calcula disolución neta/corregida de especies de ganga por día."""
    if weighted_input_df.empty or pls_df.empty:
        return pd.DataFrame()

    joined = weighted_input_df.merge(
        pls_df,
        on=["id_franja", "fecha"],
        how="inner",
    ).sort_values("fecha")

    if holdup_df is None or holdup_df.empty:
        holdup = pd.DataFrame(
            {
                "id_franja": joined["id_franja"],
                "fecha": joined["fecha"],
            }
        )
    else:
        holdup = holdup_df.copy()

    joined = joined.merge(holdup, on=["id_franja", "fecha"], how="left")

    fe_factor = calculate_drx_fe_factor(franja)

    daily = joined.copy()
    daily["cu_pls_kg"] = daily["vol_pls_m3"] * daily["cu_pls_gpl"]
    daily["acid_pls_kg"] = daily["vol_pls_m3"] * daily["acid_pls_gpl"]
    daily["fe_total_pls_kg"] = daily["vol_pls_m3"] * daily["fe_total_pls_gpl"]
    daily["fe2_pls_kg"] = daily["vol_pls_m3"] * daily["fe2_pls_gpl"]
    daily["fe3_pls_kg"] = (daily["fe_total_pls_kg"] - daily["fe2_pls_kg"]).clip(lower=0.0)
    daily["cl_pls_kg"] = daily["vol_pls_m3"] * daily["cl_pls_gpl"]
    daily["sio2_pls_kg"] = daily["vol_pls_m3"] * daily["sio2_pls_gpl"]
    daily["mn_pls_kg"] = daily["vol_pls_m3"] * daily["mn_pls_gpl"]

    daily["fe3_entrada_kg"] = (daily["fe_total_entrada_kg"] - daily["fe2_entrada_kg"]).clip(lower=0.0)

    for column in (
        "cu_holdup_delta_kg",
        "fe_total_holdup_delta_kg",
        "fe2_holdup_delta_kg",
        "cl_holdup_delta_kg",
        "sio2_holdup_delta_kg",
        "mn_holdup_delta_kg",
    ):
        if column not in daily.columns:
            daily[column] = 0.0

    daily["fe3_holdup_delta_kg"] = (
        daily.get("fe_total_holdup_delta_kg", 0.0) - daily.get("fe2_holdup_delta_kg", 0.0)
    ).clip(lower=0.0)

    daily["cu_extraido_corregido_kg"] = (
        daily["cu_pls_kg"] - daily["cu_entrada_kg"] + daily["cu_holdup_delta_kg"]
    )
    daily["fe_total_disuelto_kg"] = (
        daily["fe_total_pls_kg"] - daily["fe_total_entrada_kg"] + daily["fe_total_holdup_delta_kg"]
    )
    daily["fe2_disuelto_kg"] = (
        daily["fe2_pls_kg"] - daily["fe2_entrada_kg"] + daily["fe2_holdup_delta_kg"]
    )
    daily["fe3_disuelto_kg"] = (
        daily["fe3_pls_kg"] - daily["fe3_entrada_kg"] + daily["fe3_holdup_delta_kg"]
    )
    daily["cl_disuelto_kg"] = (
        daily["cl_pls_kg"] - daily["cl_entrada_kg"] + daily["cl_holdup_delta_kg"]
    )
    daily["sio2_disuelto_kg"] = (
        daily["sio2_pls_kg"] - daily["sio2_entrada_kg"] + daily["sio2_holdup_delta_kg"]
    )
    daily["mn_disuelto_kg"] = (
        daily["mn_pls_kg"] - daily["mn_entrada_kg"] + daily["mn_holdup_delta_kg"]
    )
    daily["fe_factor_drx"] = fe_factor
    daily["proxy_ganga_reactiva_pct"] = (
        franja.pct_goethita + franja.pct_clorita + franja.pct_arcillas
    )

    return daily
