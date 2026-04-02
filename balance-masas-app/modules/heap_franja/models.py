"""
Modelos y helpers base para el balance por franja horizontal.

Notas de unidades:
- Volumen de solución: m³
- Concentración de solución: g/L
- Masa disuelta: kg

Con estas unidades, la conversión correcta es:
    masa_kg = volumen_m3 * concentracion_gpl
porque 1 m³ = 1000 L y 1000 g = 1 kg.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


CHEMISTRY_COLUMNS = (
    "cu",
    "acid",
    "fe_total",
    "fe2",
    "cl",
    "sio2",
    "mn",
)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convierte a float respetando nulos."""
    if value is None or pd.isna(value):
        return default
    return float(value)


def parse_optional_date(value: Any) -> date | None:
    """Convierte fechas opcionales a `date`."""
    if value is None or pd.isna(value) or value == "":
        return None
    return pd.Timestamp(value).date()


def mass_kg_from_solution(volume_m3: float, concentration_gpl: float) -> float:
    """Convierte volumen y concentración de solución a masa en kg."""
    return safe_float(volume_m3) * safe_float(concentration_gpl)


def concentration_gpl_from_mass(mass_kg: float, volume_m3: float) -> float:
    """Convierte una masa disuelta a concentración g/L."""
    volume = safe_float(volume_m3)
    if volume <= 0:
        return 0.0
    return safe_float(mass_kg) / volume


def _normalize_datetime_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Normaliza columnas de fecha a timestamps sin hora."""
    normalized = df.copy()
    for column in columns:
        if column in normalized.columns:
            normalized[column] = pd.to_datetime(normalized[column], errors="coerce").dt.normalize()
    return normalized


@dataclass(frozen=True)
class Pad:
    """Pad dinámico en vista de planta."""

    id_pad: str
    nombre: str
    area_total_m2: float
    capacidad_max_franjas: int | None = None

    @classmethod
    def from_series(cls, row: pd.Series) -> "Pad":
        return cls(
            id_pad=str(row["id_pad"]),
            nombre=str(row["nombre"]),
            area_total_m2=safe_float(row["area_total_m2"]),
            capacidad_max_franjas=(
                int(row["capacidad_max_franjas"])
                if "capacidad_max_franjas" in row and not pd.isna(row["capacidad_max_franjas"])
                else None
            ),
        )


@dataclass(frozen=True)
class Ciclo:
    """Configuración de un ciclo del pad."""

    id_ciclo: str
    id_pad: str
    numero_ciclo: int
    n_franjas: int
    n_franjas_operativas: int | None
    fecha_inicio: date | None
    fecha_fin: date | None
    cut_off_acid_cu: float
    estado: str

    @classmethod
    def from_series(cls, row: pd.Series) -> "Ciclo":
        return cls(
            id_ciclo=str(row["id_ciclo"]),
            id_pad=str(row["id_pad"]),
            numero_ciclo=int(row["numero_ciclo"]),
            n_franjas=int(row["n_franjas"]),
            n_franjas_operativas=(
                int(row["n_franjas_operativas"])
                if "n_franjas_operativas" in row and not pd.isna(row["n_franjas_operativas"])
                else None
            ),
            fecha_inicio=parse_optional_date(row.get("fecha_inicio")),
            fecha_fin=parse_optional_date(row.get("fecha_fin")),
            cut_off_acid_cu=safe_float(row["cut_off_acid_cu"]),
            estado=str(row.get("estado", "activo")),
        )


@dataclass(frozen=True)
class Franja:
    """Franja horizontal, unidad de balance y muestreo."""

    id_franja: str
    id_ciclo: str
    numero_franja: int
    n_modulos: int
    operativa: bool
    fecha_on: date | None
    fecha_off: date | None
    tonelaje_t: float
    area_m2: float
    altura_m: float
    ley_cu_total_pct: float
    ley_cu_soluble_pct: float
    ley_cu_residual_pct: float | None
    humedad_residual_pct: float
    pct_goethita: float
    pct_jarosita: float
    pct_clorita: float
    pct_atacamita: float
    pct_crisocola: float
    pct_cuarzo: float
    pct_feldespatos: float
    pct_arcillas: float
    pct_mn_oxidos: float

    @property
    def cu_contenido_soluble_kg(self) -> float:
        """Cu soluble contenido en la franja."""
        return self.tonelaje_t * 1000.0 * self.ley_cu_soluble_pct / 100.0

    @property
    def recovery_from_residual_pct(self) -> float | None:
        """Recuperación inferida por ley residual al OFF."""
        if self.ley_cu_residual_pct is None or self.ley_cu_soluble_pct <= 0:
            return None
        residual_ratio = self.ley_cu_residual_pct / self.ley_cu_soluble_pct
        return max(0.0, min(100.0, (1.0 - residual_ratio) * 100.0))

    @classmethod
    def from_series(cls, row: pd.Series) -> "Franja":
        return cls(
            id_franja=str(row["id_franja"]),
            id_ciclo=str(row["id_ciclo"]),
            numero_franja=int(row["numero_franja"]),
            n_modulos=int(row["n_modulos"]),
            operativa=bool(row.get("operativa", True)),
            fecha_on=parse_optional_date(row.get("fecha_on")),
            fecha_off=parse_optional_date(row.get("fecha_off")),
            tonelaje_t=safe_float(row["tonelaje_t"]),
            area_m2=safe_float(row["area_m2"]),
            altura_m=safe_float(row["altura_m"]),
            ley_cu_total_pct=safe_float(row["ley_cu_total_pct"]),
            ley_cu_soluble_pct=safe_float(row["ley_cu_soluble_pct"]),
            ley_cu_residual_pct=(
                safe_float(row["ley_cu_residual_pct"])
                if "ley_cu_residual_pct" in row and not pd.isna(row["ley_cu_residual_pct"])
                else None
            ),
            humedad_residual_pct=safe_float(row.get("humedad_residual_pct", 10.0), 10.0),
            pct_goethita=safe_float(row.get("pct_goethita")),
            pct_jarosita=safe_float(row.get("pct_jarosita")),
            pct_clorita=safe_float(row.get("pct_clorita")),
            pct_atacamita=safe_float(row.get("pct_atacamita")),
            pct_crisocola=safe_float(row.get("pct_crisocola")),
            pct_cuarzo=safe_float(row.get("pct_cuarzo")),
            pct_feldespatos=safe_float(row.get("pct_feldespatos")),
            pct_arcillas=safe_float(row.get("pct_arcillas")),
            pct_mn_oxidos=safe_float(row.get("pct_mn_oxidos")),
        )


@dataclass(frozen=True)
class Modulo:
    """Subdivisión de riego dentro de una franja."""

    id_modulo: str
    id_franja: str
    numero_modulo: int
    area_m2: float
    tonelaje_estimado_t: float | None = None

    @classmethod
    def from_series(cls, row: pd.Series) -> "Modulo":
        return cls(
            id_modulo=str(row["id_modulo"]),
            id_franja=str(row["id_franja"]),
            numero_modulo=int(row["numero_modulo"]),
            area_m2=safe_float(row["area_m2"]),
            tonelaje_estimado_t=(
                safe_float(row["tonelaje_estimado_t"])
                if "tonelaje_estimado_t" in row and not pd.isna(row["tonelaje_estimado_t"])
                else None
            ),
        )


@dataclass(frozen=True)
class RuteoModulo:
    """Regla de ruteo vigente para un módulo."""

    id_modulo: str
    fecha_inicio: date | None
    fecha_fin: date | None
    tipo_solucion: str
    fuente_ils: str | None
    notas: str = ""

    @classmethod
    def from_series(cls, row: pd.Series) -> "RuteoModulo":
        fuente = row.get("fuente_ils")
        return cls(
            id_modulo=str(row["id_modulo"]),
            fecha_inicio=parse_optional_date(row.get("fecha_inicio")),
            fecha_fin=parse_optional_date(row.get("fecha_fin")),
            tipo_solucion=str(row["tipo_solucion"]),
            fuente_ils=None if pd.isna(fuente) or fuente == "" else str(fuente),
            notas=str(row.get("notas", "")),
        )


@dataclass(frozen=True)
class DatosRiegoModulo:
    """Dato operacional diario por módulo."""

    id_modulo: str
    id_franja: str
    fecha: date
    tipo_solucion: str
    fuente_ils: str | None
    vol_aplicado_m3: float
    tasa_riego_lhm2: float
    cu_entrada_gpl: float
    acid_entrada_gpl: float
    fe_total_entrada_gpl: float
    fe2_entrada_gpl: float
    cl_entrada_gpl: float
    sio2_entrada_gpl: float
    mn_entrada_gpl: float

    @classmethod
    def from_series(cls, row: pd.Series) -> "DatosRiegoModulo":
        fuente = row.get("fuente_ils")
        return cls(
            id_modulo=str(row["id_modulo"]),
            id_franja=str(row["id_franja"]),
            fecha=pd.Timestamp(row["fecha"]).date(),
            tipo_solucion=str(row["tipo_solucion"]),
            fuente_ils=None if pd.isna(fuente) or fuente == "" else str(fuente),
            vol_aplicado_m3=safe_float(row["vol_aplicado_m3"]),
            tasa_riego_lhm2=safe_float(row["tasa_riego_lhm2"]),
            cu_entrada_gpl=safe_float(row["cu_entrada_gpl"]),
            acid_entrada_gpl=safe_float(row["acid_entrada_gpl"]),
            fe_total_entrada_gpl=safe_float(row["fe_total_entrada_gpl"]),
            fe2_entrada_gpl=safe_float(row["fe2_entrada_gpl"]),
            cl_entrada_gpl=safe_float(row["cl_entrada_gpl"]),
            sio2_entrada_gpl=safe_float(row["sio2_entrada_gpl"]),
            mn_entrada_gpl=safe_float(row["mn_entrada_gpl"]),
        )


@dataclass(frozen=True)
class DatosPLSFranja:
    """Dato operacional diario de PLS medido por franja."""

    id_franja: str
    fecha: date
    vol_pls_m3: float
    cu_pls_gpl: float
    acid_pls_gpl: float
    fe_total_pls_gpl: float
    fe2_pls_gpl: float
    cl_pls_gpl: float
    sio2_pls_gpl: float
    mn_pls_gpl: float

    @classmethod
    def from_series(cls, row: pd.Series) -> "DatosPLSFranja":
        return cls(
            id_franja=str(row["id_franja"]),
            fecha=pd.Timestamp(row["fecha"]).date(),
            vol_pls_m3=safe_float(row["vol_pls_m3"]),
            cu_pls_gpl=safe_float(row["cu_pls_gpl"]),
            acid_pls_gpl=safe_float(row["acid_pls_gpl"]),
            fe_total_pls_gpl=safe_float(row["fe_total_pls_gpl"]),
            fe2_pls_gpl=safe_float(row["fe2_pls_gpl"]),
            cl_pls_gpl=safe_float(row["cl_pls_gpl"]),
            sio2_pls_gpl=safe_float(row["sio2_pls_gpl"]),
            mn_pls_gpl=safe_float(row["mn_pls_gpl"]),
        )


@dataclass(frozen=True)
class EntradaPonderada:
    """Entrada ponderada diaria desde módulos hacia la franja."""

    id_franja: str
    fecha: date
    vol_total_m3: float
    vol_refino_m3: float
    vol_ils_m3: float
    n_modulos_regados: int
    n_modulos_refino: int
    n_modulos_ils: int
    cu_entrada_kg: float
    acid_entrada_kg: float
    fe_total_entrada_kg: float
    fe2_entrada_kg: float
    cl_entrada_kg: float
    sio2_entrada_kg: float
    mn_entrada_kg: float
    cu_entrada_gpl: float
    acid_entrada_gpl: float
    fe_total_entrada_gpl: float
    fe2_entrada_gpl: float
    fe3_entrada_gpl: float
    cl_entrada_gpl: float
    sio2_entrada_gpl: float
    mn_entrada_gpl: float
    fuente_ils_volumenes: dict[str, float] = field(default_factory=dict)
    fase_dominante: str = "mixto"

    def to_record(self) -> dict[str, Any]:
        """Convierte la dataclass a un registro plano para DataFrame."""
        return {
            "id_franja": self.id_franja,
            "fecha": pd.Timestamp(self.fecha),
            "vol_total_m3": self.vol_total_m3,
            "vol_refino_m3": self.vol_refino_m3,
            "vol_ils_m3": self.vol_ils_m3,
            "n_modulos_regados": self.n_modulos_regados,
            "n_modulos_refino": self.n_modulos_refino,
            "n_modulos_ils": self.n_modulos_ils,
            "cu_entrada_kg": self.cu_entrada_kg,
            "acid_entrada_kg": self.acid_entrada_kg,
            "fe_total_entrada_kg": self.fe_total_entrada_kg,
            "fe2_entrada_kg": self.fe2_entrada_kg,
            "cl_entrada_kg": self.cl_entrada_kg,
            "sio2_entrada_kg": self.sio2_entrada_kg,
            "mn_entrada_kg": self.mn_entrada_kg,
            "cu_entrada_gpl": self.cu_entrada_gpl,
            "acid_entrada_gpl": self.acid_entrada_gpl,
            "fe_total_entrada_gpl": self.fe_total_entrada_gpl,
            "fe2_entrada_gpl": self.fe2_entrada_gpl,
            "fe3_entrada_gpl": self.fe3_entrada_gpl,
            "cl_entrada_gpl": self.cl_entrada_gpl,
            "sio2_entrada_gpl": self.sio2_entrada_gpl,
            "mn_entrada_gpl": self.mn_entrada_gpl,
            "fuente_ils_volumenes": self.fuente_ils_volumenes,
            "fase_dominante": self.fase_dominante,
        }


@dataclass(frozen=True)
class CopperBalanceSummary:
    """Resumen de balance de cobre por franja."""

    id_franja: str
    cu_contenido_soluble_kg: float
    cu_extraido_directo_kg: float
    cu_extraido_reconciliado_kg: float
    recovery_direct_pct: float
    recovery_residual_pct: float | None
    recovery_pct: float
    recovery_gap_pct_points: float | None
    cu_fase_refino_kg: float
    cu_fase_ils_kg: float
    cu_fase_mixto_kg: float
    efic_refino_kg_m3: float
    efic_ils_kg_m3: float
    efic_mixto_kg_m3: float
    dias_balance: int


@dataclass(frozen=True)
class AcidBalanceSummary:
    """Resumen de balance de ácido por franja."""

    id_franja: str
    acid_consumido_total_kg: float
    acid_por_cu_kg: float
    acid_por_fe_kg: float
    acid_por_cl_kg: float
    acid_por_sio2_kg: float
    acid_por_mn_kg: float
    acid_no_asignado_kg: float
    acid_sobre_asignado_kg: float
    acid_cierre_pct: float
    ratio_acid_cu_kgkg: float
    factor_drx_fe: float


@dataclass(frozen=True)
class LeachRatioSummary:
    """Resumen de razón de lixiviación por franja."""

    id_franja: str
    rl_total_m3_t: float
    rl_refino_m3_t: float
    rl_ils_m3_t: float
    rl_por_area_m: float
    rl_por_altura: float
    tasa_global_m3_m2_dia: float
    rl_por_fuente_m3_t: dict[str, float]
    fase_dominante_global: str


@dataclass(frozen=True)
class ModuleIrrigationMetric:
    """KPI de riego por módulo."""

    id_modulo: str
    id_franja: str
    vol_aplicado_total_m3: float
    rl_total_m3_t: float
    rl_refino_m3_t: float
    rl_ils_m3_t: float
    dias_refino: int
    dias_ils: int
    dias_reposo: int
    acid_refino_kg: float
    acid_ils_kg: float
    uniformidad_ratio: float
    fuentes_ils: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        """Convierte la métrica a un registro plano."""
        return {
            "id_modulo": self.id_modulo,
            "id_franja": self.id_franja,
            "vol_aplicado_total_m3": self.vol_aplicado_total_m3,
            "rl_total_m3_t": self.rl_total_m3_t,
            "rl_refino_m3_t": self.rl_refino_m3_t,
            "rl_ils_m3_t": self.rl_ils_m3_t,
            "dias_refino": self.dias_refino,
            "dias_ils": self.dias_ils,
            "dias_reposo": self.dias_reposo,
            "acid_refino_kg": self.acid_refino_kg,
            "acid_ils_kg": self.acid_ils_kg,
            "uniformidad_ratio": self.uniformidad_ratio,
            "fuentes_ils": ", ".join(self.fuentes_ils),
        }


@dataclass
class HeapFranjaDataset:
    """Conjunto de datos cargado desde `data/synthetic/`."""

    base_path: Path
    pads_df: pd.DataFrame
    ciclos_df: pd.DataFrame
    franjas_df: pd.DataFrame
    modulos_df: pd.DataFrame
    ruteo_df: pd.DataFrame
    riego_df: pd.DataFrame
    pls_df: pd.DataFrame
    pads: dict[str, Pad]
    ciclos: dict[str, Ciclo]
    franjas: dict[str, Franja]
    modulos: dict[str, Modulo]
    ruteos: list[RuteoModulo]

    @classmethod
    def from_csv_dir(cls, base_path: str | Path) -> "HeapFranjaDataset":
        """Carga todos los CSVs sintéticos disponibles."""
        root = Path(base_path)
        pads_df = pd.read_csv(root / "pads.csv")
        ciclos_df = _normalize_datetime_columns(
            pd.read_csv(root / "ciclos.csv"),
            ["fecha_inicio", "fecha_fin"],
        )
        franjas_df = _normalize_datetime_columns(
            pd.read_csv(root / "franjas.csv"),
            ["fecha_on", "fecha_off"],
        )
        modulos_df = pd.read_csv(root / "modulos.csv")
        ruteo_df = _normalize_datetime_columns(
            pd.read_csv(root / "ruteo.csv"),
            ["fecha_inicio", "fecha_fin"],
        )
        riego_df = _normalize_datetime_columns(
            pd.read_csv(root / "riego_diario.csv"),
            ["fecha"],
        )
        pls_df = _normalize_datetime_columns(
            pd.read_csv(root / "pls_diario.csv"),
            ["fecha"],
        )

        pads = {row["id_pad"]: Pad.from_series(row) for _, row in pads_df.iterrows()}
        ciclos = {row["id_ciclo"]: Ciclo.from_series(row) for _, row in ciclos_df.iterrows()}
        franjas = {
            row["id_franja"]: Franja.from_series(row)
            for _, row in franjas_df.iterrows()
        }
        modulos = {
            row["id_modulo"]: Modulo.from_series(row)
            for _, row in modulos_df.iterrows()
        }
        ruteos = [RuteoModulo.from_series(row) for _, row in ruteo_df.iterrows()]

        return cls(
            base_path=root,
            pads_df=pads_df,
            ciclos_df=ciclos_df,
            franjas_df=franjas_df,
            modulos_df=modulos_df,
            ruteo_df=ruteo_df,
            riego_df=riego_df,
            pls_df=pls_df,
            pads=pads,
            ciclos=ciclos,
            franjas=franjas,
            modulos=modulos,
            ruteos=ruteos,
        )

    def get_ciclos(self) -> list[Ciclo]:
        """Retorna ciclos ordenados por fecha de inicio."""
        ordered = self.ciclos_df.sort_values("fecha_inicio", na_position="last")["id_ciclo"]
        return [self.ciclos[str(ciclo_id)] for ciclo_id in ordered]

    def get_franjas_by_ciclo(
        self,
        id_ciclo: str,
        operativas_only: bool = True,
    ) -> list[Franja]:
        """Retorna franjas de un ciclo, opcionalmente solo operativas."""
        filtered = self.franjas_df[self.franjas_df["id_ciclo"] == id_ciclo].copy()
        if operativas_only:
            filtered = filtered[filtered["operativa"]]
        filtered = filtered.sort_values("numero_franja")
        return [self.franjas[str(row["id_franja"])] for _, row in filtered.iterrows()]

    def get_franja(self, id_franja: str) -> Franja:
        """Obtiene una franja por id."""
        return self.franjas[id_franja]

    def get_ciclo(self, id_ciclo: str) -> Ciclo:
        """Obtiene un ciclo por id."""
        return self.ciclos[id_ciclo]

    def get_modulos_by_franja(self, id_franja: str) -> pd.DataFrame:
        """Retorna el detalle de módulos de una franja."""
        return (
            self.modulos_df[self.modulos_df["id_franja"] == id_franja]
            .copy()
            .sort_values("numero_modulo")
            .reset_index(drop=True)
        )

    def get_riego_by_franja(self, id_franja: str) -> pd.DataFrame:
        """Retorna la serie diaria de riego por módulo de una franja."""
        return (
            self.riego_df[self.riego_df["id_franja"] == id_franja]
            .copy()
            .sort_values(["fecha", "id_modulo"])
            .reset_index(drop=True)
        )

    def get_pls_by_franja(self, id_franja: str) -> pd.DataFrame:
        """Retorna la serie diaria de PLS de una franja."""
        return (
            self.pls_df[self.pls_df["id_franja"] == id_franja]
            .copy()
            .sort_values("fecha")
            .reset_index(drop=True)
        )

    def get_ruteo_by_franja(self, id_franja: str) -> pd.DataFrame:
        """Retorna historial de ruteo de todos los módulos de una franja."""
        modulos = set(self.get_modulos_by_franja(id_franja)["id_modulo"].tolist())
        return (
            self.ruteo_df[self.ruteo_df["id_modulo"].isin(modulos)]
            .copy()
            .sort_values(["id_modulo", "fecha_inicio"])
            .reset_index(drop=True)
        )
