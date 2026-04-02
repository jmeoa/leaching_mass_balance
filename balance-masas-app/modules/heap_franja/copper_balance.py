"""Balance directo de cobre por franja."""

from __future__ import annotations

import pandas as pd

from modules.heap_franja.holdup import build_holdup_profile
from modules.heap_franja.models import CopperBalanceSummary, Franja
from modules.heap_franja.weighted_input import calculate_weighted_input


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_copper_balance(
    franja: Franja,
    riego_df: pd.DataFrame,
    pls_df: pd.DataFrame,
    weighted_input_df: pd.DataFrame | None = None,
    holdup_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, CopperBalanceSummary]:
    """Calcula balance diario y acumulado de cobre."""
    weighted = weighted_input_df if weighted_input_df is not None else calculate_weighted_input(riego_df)
    holdup = holdup_df if holdup_df is not None else build_holdup_profile(franja, weighted, pls_df)

    joined = weighted.merge(
        pls_df,
        on=["id_franja", "fecha"],
        how="inner",
    ).sort_values("fecha")

    joined = joined.merge(
        holdup[
            [
                "id_franja",
                "fecha",
                "holdup_actual_m3",
                "holdup_fill_pct",
                "cu_holdup_prev_kg",
                "cu_holdup_actual_kg",
                "cu_holdup_delta_kg",
            ]
        ],
        on=["id_franja", "fecha"],
        how="left",
    )

    daily = joined.copy()
    daily["cu_pls_kg"] = daily["vol_pls_m3"] * daily["cu_pls_gpl"]
    daily["cu_extraido_directo_kg"] = daily["cu_pls_kg"] - daily["cu_entrada_kg"]
    daily["cu_extraido_corregido_kg"] = (
        daily["cu_extraido_directo_kg"] + daily["cu_holdup_delta_kg"].fillna(0.0)
    )
    daily["cu_extraido_directo_acum_kg"] = daily["cu_extraido_corregido_kg"].cumsum()
    daily["recovery_direct_pct"] = (
        daily["cu_extraido_directo_acum_kg"] / franja.cu_contenido_soluble_kg * 100.0
    )

    recovery_residual_pct = franja.recovery_from_residual_pct
    if recovery_residual_pct is not None:
        recovery_reconciled_pct = (
            daily["recovery_direct_pct"] * 0.4 + recovery_residual_pct * 0.6
        )
    else:
        recovery_reconciled_pct = daily["recovery_direct_pct"]

    daily["recovery_reconciled_pct"] = recovery_reconciled_pct
    daily["recovery_residual_pct"] = recovery_residual_pct

    phase_map = {
        "refino": "cu_fase_refino_kg",
        "ils": "cu_fase_ils_kg",
        "mixto": "cu_fase_mixto_kg",
    }
    phase_totals = {value: 0.0 for value in phase_map.values()}
    phase_volumes = {phase: 0.0 for phase in phase_map}

    for row in daily.to_dict("records"):
        phase = str(row["fase_dominante"])
        if phase not in phase_map:
            phase = "mixto"
        phase_totals[phase_map[phase]] += float(row["cu_extraido_corregido_kg"])
        phase_volumes[phase] += float(row["vol_total_m3"])

    summary = CopperBalanceSummary(
        id_franja=franja.id_franja,
        cu_contenido_soluble_kg=franja.cu_contenido_soluble_kg,
        cu_extraido_directo_kg=float(daily["cu_extraido_directo_acum_kg"].iloc[-1]),
        cu_extraido_reconciliado_kg=float(
            franja.cu_contenido_soluble_kg
            * float(daily["recovery_reconciled_pct"].iloc[-1])
            / 100.0
        ),
        recovery_direct_pct=float(daily["recovery_direct_pct"].iloc[-1]),
        recovery_residual_pct=recovery_residual_pct,
        recovery_pct=float(daily["recovery_reconciled_pct"].iloc[-1]),
        recovery_gap_pct_points=(
            float(daily["recovery_reconciled_pct"].iloc[-1] - daily["recovery_direct_pct"].iloc[-1])
            if recovery_residual_pct is not None
            else None
        ),
        cu_fase_refino_kg=phase_totals["cu_fase_refino_kg"],
        cu_fase_ils_kg=phase_totals["cu_fase_ils_kg"],
        cu_fase_mixto_kg=phase_totals["cu_fase_mixto_kg"],
        efic_refino_kg_m3=_safe_ratio(
            phase_totals["cu_fase_refino_kg"],
            phase_volumes["refino"],
        ),
        efic_ils_kg_m3=_safe_ratio(
            phase_totals["cu_fase_ils_kg"],
            phase_volumes["ils"],
        ),
        efic_mixto_kg_m3=_safe_ratio(
            phase_totals["cu_fase_mixto_kg"],
            phase_volumes["mixto"],
        ),
        dias_balance=int(len(daily)),
    )
    return daily.reset_index(drop=True), summary
