"""Carga, validación y generación de input mensual para la app FastAPI."""

from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from config import DEFAULT_CONFIG
from modules.heap_franja import (
    HeapFranjaDataset,
    calculate_acid_balance,
    calculate_copper_balance,
    calculate_weighted_input,
)


EXPECTED_MONTHLY_COLUMNS = [
    "periodo",
    "mineral_alimentado_ton",
    "ley_cu_alimentada",
    "vol_pls_m3",
    "cu_pls_gpl",
    "acid_pls_gpl",
    "vol_refino_m3",
    "cu_refino_gpl",
    "acid_refino_gpl",
    "vol_acuoso_cargado_m3",
    "cu_acuoso_cargado_gpl",
    "vol_electrolito_rico_m3",
    "cu_electrolito_rico_gpl",
    "acid_electrolito_rico_gpl",
    "vol_electrolito_pobre_m3",
    "cu_electrolito_pobre_gpl",
    "acid_electrolito_pobre_gpl",
    "catodos_ton",
    "eficiencia_corriente",
    "acid_makeup_ton",
    "pilas_activas_inventario",
]


COLUMN_ALIASES = {
    "period": "periodo",
    "mes": "periodo",
    "periodo_mes": "periodo",
    "mineral_alimentado_t": "mineral_alimentado_ton",
    "ley_cu_alimentada_pct": "ley_cu_alimentada",
    "cu_pls": "cu_pls_gpl",
    "acid_pls": "acid_pls_gpl",
    "cu_refino": "cu_refino_gpl",
    "acid_refino": "acid_refino_gpl",
    "cu_acuoso_cargado": "cu_acuoso_cargado_gpl",
    "cu_electrolito_rico": "cu_electrolito_rico_gpl",
    "acid_electrolito_rico": "acid_electrolito_rico_gpl",
    "cu_electrolito_pobre": "cu_electrolito_pobre_gpl",
    "acid_electrolito_pobre": "acid_electrolito_pobre_gpl",
    "catodos": "catodos_ton",
}


NUMERIC_COLUMNS = [
    column
    for column in EXPECTED_MONTHLY_COLUMNS
    if column not in ("periodo", "pilas_activas_inventario")
]


def _month_start(value: Any) -> pd.Timestamp:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"Periodo inválido: {value!r}")
    return timestamp.to_period("M").to_timestamp()


def _weighted_average(df: pd.DataFrame, value_col: str, weight_col: str) -> float:
    if df.empty or df[weight_col].sum() <= 0:
        return 0.0
    return float((df[value_col] * df[weight_col]).sum() / df[weight_col].sum())


def normalize_monthly_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Homologa nombres de columnas a la plantilla estándar."""
    normalized = df.copy()
    normalized.columns = [
        COLUMN_ALIASES.get(str(column).strip().lower(), str(column).strip().lower())
        for column in normalized.columns
    ]
    return normalized


def validate_monthly_input(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Valida y tipa el input mensual."""
    issues: List[Dict[str, Any]] = []
    normalized = normalize_monthly_columns(df)

    missing = [column for column in EXPECTED_MONTHLY_COLUMNS if column not in normalized.columns]
    if missing:
        issues.append(
            {
                "level": "error",
                "code": "missing_columns",
                "message": f"Faltan columnas obligatorias: {', '.join(missing)}",
            }
        )
        return normalized, issues

    validated = normalized[EXPECTED_MONTHLY_COLUMNS].copy()
    try:
        validated["periodo"] = validated["periodo"].map(_month_start)
    except ValueError as exc:
        issues.append({"level": "error", "code": "invalid_period", "message": str(exc)})
        return validated, issues

    for column in NUMERIC_COLUMNS:
        validated[column] = pd.to_numeric(validated[column], errors="coerce")
        if validated[column].isna().any():
            issues.append(
                {
                    "level": "error",
                    "code": "invalid_numeric",
                    "message": f"Hay valores no numéricos en {column}",
                }
            )

    if validated["periodo"].duplicated().any():
        issues.append(
            {
                "level": "warning",
                "code": "duplicated_period",
                "message": "Hay períodos repetidos; al procesar se consolidarán por el último registro.",
            }
        )

    for column in ["ley_cu_alimentada", "eficiencia_corriente"]:
        out_of_range = validated[column].lt(0).any()
        if out_of_range:
            issues.append(
                {
                    "level": "warning",
                    "code": "negative_value",
                    "message": f"Se detectaron valores negativos en {column}",
                }
            )

    validated["pilas_activas_inventario"] = validated["pilas_activas_inventario"].fillna("[]")
    validated = validated.sort_values("periodo").reset_index(drop=True)
    return validated, issues


def load_tabular_file(content: bytes, filename: str) -> pd.DataFrame:
    """Carga CSV o Excel desde bytes."""
    suffix = Path(filename).suffix.lower()
    buffer = io.BytesIO(content)
    if suffix == ".csv":
        return pd.read_csv(buffer)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(buffer)
    raise ValueError(f"Formato no soportado: {suffix}")


def load_monthly_input_file(content: bytes, filename: str) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Carga y valida un archivo de input mensual."""
    raw = load_tabular_file(content, filename)
    return validate_monthly_input(raw)


def _build_inventory_snapshot(dataset: HeapFranjaDataset, period_end: pd.Timestamp) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for franja in dataset.franjas.values():
        if franja.fecha_on is None:
            continue
        if pd.Timestamp(franja.fecha_on) > period_end:
            continue

        riego_df = dataset.get_riego_by_franja(franja.id_franja)
        pls_df = dataset.get_pls_by_franja(franja.id_franja)
        riego_df = riego_df[riego_df["fecha"] <= period_end].copy()
        pls_df = pls_df[pls_df["fecha"] <= period_end].copy()

        recovery_pct = 0.0
        if not riego_df.empty and not pls_df.empty:
            weighted_df = calculate_weighted_input(riego_df)
            copper_daily_df, copper_summary = calculate_copper_balance(
                franja,
                riego_df,
                pls_df,
                weighted_input_df=weighted_df,
            )
            acid_daily_df, acid_summary = calculate_acid_balance(
                franja,
                riego_df,
                pls_df,
                weighted_input_df=weighted_df,
                copper_daily_df=copper_daily_df,
            )
            recovery_pct = float(copper_summary.recovery_pct)
            acid_ratio = float(acid_summary.ratio_acid_cu_kgkg)
        else:
            acid_ratio = 0.0

        remaining_cu_t = franja.cu_contenido_soluble_kg * max(0.0, 1.0 - recovery_pct / 100.0) / 1000.0
        if franja.fecha_off and pd.Timestamp(franja.fecha_off) < period_end:
            state = "agotada"
        elif recovery_pct <= 1:
            state = "apilando"
        elif recovery_pct >= 90:
            state = "drenando"
        else:
            state = "regando"

        snapshots.append(
            {
                "id_pila": franja.id_franja,
                "fecha_on": str(franja.fecha_on) if franja.fecha_on else None,
                "fecha_off": str(franja.fecha_off) if franja.fecha_off else None,
                "ton_mineral": franja.tonelaje_t,
                "ley_cu": franja.ley_cu_total_pct,
                "cu_remanente_t": round(remaining_cu_t, 2),
                "recuperacion_pct": round(recovery_pct, 2),
                "acid_ratio_kgkg": round(acid_ratio, 2),
                "estado": state,
            }
        )
    return snapshots


@lru_cache(maxsize=4)
def build_synthetic_monthly_input(base_path: Path | None = None) -> pd.DataFrame:
    """Deriva un input mensual sintético desde la base diaria del pad horizontal."""
    root = base_path or Path(__file__).resolve().parents[1] / "data" / "synthetic"
    dataset = HeapFranjaDataset.from_csv_dir(root)

    riego_df = dataset.riego_df.copy()
    pls_df = dataset.pls_df.copy()
    franjas_df = dataset.franjas_df.copy()

    riego_df["periodo"] = pd.to_datetime(riego_df["fecha"]).dt.to_period("M").dt.to_timestamp()
    pls_df["periodo"] = pd.to_datetime(pls_df["fecha"]).dt.to_period("M").dt.to_timestamp()
    franjas_df["fecha_on"] = pd.to_datetime(franjas_df["fecha_on"], errors="coerce")
    franjas_df["fecha_off"] = pd.to_datetime(franjas_df["fecha_off"], errors="coerce")

    all_periods = sorted(
        set(riego_df["periodo"].dropna().unique().tolist()) | set(pls_df["periodo"].dropna().unique().tolist())
    )

    rows: List[Dict[str, Any]] = []
    for period in all_periods:
        period_ts = pd.Timestamp(period)
        month_end = period_ts + pd.offsets.MonthEnd(0)
        period_riego = riego_df[riego_df["periodo"] == period_ts].copy()
        period_pls = pls_df[pls_df["periodo"] == period_ts].copy()
        period_refino = period_riego[period_riego["tipo_solucion"] == "refino"].copy()
        new_franjas = franjas_df[franjas_df["fecha_on"].dt.to_period("M") == period_ts.to_period("M")].copy()

        mineral_alimentado_ton = float(new_franjas["tonelaje_t"].sum()) if not new_franjas.empty else 0.0
        if not new_franjas.empty and new_franjas["tonelaje_t"].sum() > 0:
            ley_cu_alimentada = float(
                (new_franjas["tonelaje_t"] * new_franjas["ley_cu_total_pct"]).sum() / new_franjas["tonelaje_t"].sum()
            )
        else:
            ley_cu_alimentada = 0.0

        vol_pls_m3 = float(period_pls["vol_pls_m3"].sum())
        cu_pls_gpl = _weighted_average(period_pls, "cu_pls_gpl", "vol_pls_m3")
        acid_pls_gpl = _weighted_average(period_pls, "acid_pls_gpl", "vol_pls_m3")

        vol_refino_m3 = float(period_refino["vol_aplicado_m3"].sum())
        cu_refino_gpl = _weighted_average(period_refino, "cu_entrada_gpl", "vol_aplicado_m3")
        acid_refino_gpl = _weighted_average(period_refino, "acid_entrada_gpl", "vol_aplicado_m3")

        cu_pls_kg = vol_pls_m3 * cu_pls_gpl
        cu_refino_kg = vol_refino_m3 * cu_refino_gpl
        cu_transferido_sx_kg = max(cu_pls_kg - cu_refino_kg, 0.0) * 0.92

        cu_electrolito_rico_gpl = 44.0
        cu_electrolito_pobre_gpl = 31.0
        acid_electrolito_rico_gpl = 168.0
        acid_electrolito_pobre_gpl = 188.0
        vol_electrolito_rico_m3 = cu_transferido_sx_kg / max(cu_electrolito_rico_gpl - cu_electrolito_pobre_gpl, 1.0)
        vol_electrolito_pobre_m3 = vol_electrolito_rico_m3 * 0.98
        catodos_ton = cu_transferido_sx_kg * 0.965 / 1000.0
        eficiencia_corriente = 90.0 + float(period_ts.month % 4)

        acid_consumido_lix_kg = max(vol_refino_m3 * acid_refino_gpl - vol_pls_m3 * acid_pls_gpl, 0.0)
        acid_makeup_ton = max(acid_consumido_lix_kg / 1000.0 * 0.18, catodos_ton * 0.22)

        rows.append(
            {
                "periodo": period_ts,
                "mineral_alimentado_ton": round(mineral_alimentado_ton, 2),
                "ley_cu_alimentada": round(ley_cu_alimentada, 4),
                "vol_pls_m3": round(vol_pls_m3, 2),
                "cu_pls_gpl": round(cu_pls_gpl, 3),
                "acid_pls_gpl": round(acid_pls_gpl, 3),
                "vol_refino_m3": round(vol_refino_m3, 2),
                "cu_refino_gpl": round(cu_refino_gpl, 3),
                "acid_refino_gpl": round(acid_refino_gpl, 3),
                "vol_acuoso_cargado_m3": round(vol_pls_m3, 2),
                "cu_acuoso_cargado_gpl": round(cu_pls_gpl, 3),
                "vol_electrolito_rico_m3": round(vol_electrolito_rico_m3, 2),
                "cu_electrolito_rico_gpl": cu_electrolito_rico_gpl,
                "acid_electrolito_rico_gpl": acid_electrolito_rico_gpl,
                "vol_electrolito_pobre_m3": round(vol_electrolito_pobre_m3, 2),
                "cu_electrolito_pobre_gpl": cu_electrolito_pobre_gpl,
                "acid_electrolito_pobre_gpl": acid_electrolito_pobre_gpl,
                "catodos_ton": round(catodos_ton, 3),
                "eficiencia_corriente": round(eficiencia_corriente, 1),
                "acid_makeup_ton": round(acid_makeup_ton, 3),
                "pilas_activas_inventario": json.dumps(_build_inventory_snapshot(dataset, month_end), ensure_ascii=False),
            }
        )

    synthetic_df = pd.DataFrame(rows)
    validated_df, _ = validate_monthly_input(synthetic_df)
    return validated_df


def get_default_monthly_input() -> pd.DataFrame:
    """Retorna la base mensual por defecto."""
    return build_synthetic_monthly_input().copy()
