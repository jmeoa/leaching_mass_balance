"""Curvas metalúrgicas Rec vs RL y proyección de cut-off."""

from __future__ import annotations

from typing import Dict

import pandas as pd


def build_recovery_vs_rl_curve(copper_daily_df: pd.DataFrame, rl_daily_df: pd.DataFrame) -> pd.DataFrame:
    """Une recuperación y RL acumulada en una sola curva."""
    if copper_daily_df.empty or rl_daily_df.empty:
        return pd.DataFrame()
    merged = copper_daily_df.merge(
        rl_daily_df[["fecha", "rl_total_acum_m3_t", "rl_refino_acum_m3_t", "rl_ils_acum_m3_t"]],
        on="fecha",
        how="inner",
    )
    return merged[
        [
            "fecha",
            "rl_total_acum_m3_t",
            "rl_refino_acum_m3_t",
            "rl_ils_acum_m3_t",
            "recovery_direct_pct",
            "recovery_reconciled_pct",
            "recovery_residual_pct",
        ]
    ].copy()


def project_cutoff_day(acid_daily_df: pd.DataFrame, copper_daily_df: pd.DataFrame, cut_off_acid_cu: float) -> Dict[str, object]:
    """Estima el primer día en que se alcanza el cut-off ácido/Cu."""
    if acid_daily_df.empty or copper_daily_df.empty:
        return {"cutoff_reached": False, "fecha": None, "ratio": None}
    merged = acid_daily_df[["fecha", "acid_consumido_kg"]].merge(
        copper_daily_df[["fecha", "cu_extraido_corregido_kg"]],
        on="fecha",
        how="inner",
    )
    merged["acid_consumido_acum_kg"] = merged["acid_consumido_kg"].cumsum()
    merged["cu_extraido_acum_kg"] = merged["cu_extraido_corregido_kg"].cumsum()
    merged["ratio_acid_cu_kgkg"] = merged["acid_consumido_acum_kg"] / merged["cu_extraido_acum_kg"].replace(0, pd.NA)
    reached = merged[merged["ratio_acid_cu_kgkg"] >= cut_off_acid_cu]
    if reached.empty:
        return {"cutoff_reached": False, "fecha": None, "ratio": None}
    first = reached.iloc[0]
    return {
        "cutoff_reached": True,
        "fecha": str(pd.Timestamp(first["fecha"]).date()),
        "ratio": float(first["ratio_acid_cu_kgkg"]),
    }
