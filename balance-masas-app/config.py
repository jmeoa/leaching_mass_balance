"""
Configuración global y factores estequiométricos default.

Todos los factores son editables por el usuario en la app.
Los valores default provienen de estequiometría ideal y deben
ajustarse con data real de cada operación.
"""
from dataclasses import dataclass, field


@dataclass
class FactoresEstequiometricos:
    """Factores de consumo de ácido por especie (kg H₂SO₄ / kg elemento)."""

    # Cobre
    # CuO + H₂SO₄ → CuSO₄ + H₂O  (1 mol Cu = 63.5g → 1 mol H₂SO₄ = 98g)
    acid_por_cu: float = 1.543  # kg H₂SO₄ / kg Cu

    # Hierro — ponderado por mineralogía
    # Goethita: 2FeOOH + 3H₂SO₄ → Fe₂(SO₄)₃ + 4H₂O
    acid_por_fe_goethita: float = 2.63  # kg H₂SO₄ / kg Fe
    # Clorita: compleja, rango 1.5-2.5
    acid_por_fe_clorita: float = 2.0  # kg H₂SO₄ / kg Fe

    # Cloruro (vía atacamita)
    # Cu₂Cl(OH)₃ + 3/2 H₂SO₄ → ...
    acid_por_cl_atacamita: float = 2.8  # kg H₂SO₄ / kg Cl⁻

    # Sílice (silicatos: crisocola, arcillas)
    acid_por_sio2: float = 1.63  # kg H₂SO₄ / kg SiO₂

    # Manganeso
    # MnO₂ + H₂SO₄ → MnSO₄ + H₂O + ½O₂
    acid_por_mn: float = 1.78  # kg H₂SO₄ / kg Mn

    # Ácido generado en EW (estequiométrico)
    acid_generado_ew: float = 1.54  # kg H₂SO₄ / kg Cu depositado


@dataclass
class ParametrosDefault:
    """Parámetros operacionales default."""

    # Holdup
    humedad_residual_default_pct: float = 10.0  # %
    densidad_solucion_ton_m3: float = 1.05  # t/m³

    # Alertas
    umbral_desbalance_hidrico_pct: float = 20.0  # %
    umbral_acid_no_asignado_pct: float = 30.0  # %
    umbral_reconciliacion_pp: float = 5.0  # puntos porcentuales
    umbral_uniformidad_riego_pct: float = 20.0  # % desviación del promedio
    umbral_cu_pls_minimo_gpl: float = 0.3  # g/L

    # Clasificación de dominancia de tipo de solución
    umbral_dominancia_pct: float = 70.0  # % vol para clasificar fase refino/ILS


@dataclass
class AppConfig:
    """Configuración general de la aplicación."""

    factores: FactoresEstequiometricos = field(
        default_factory=FactoresEstequiometricos
    )
    parametros: ParametrosDefault = field(default_factory=ParametrosDefault)

    # Google Sheets
    gsheets_spreadsheet_name: str = "BalanceMasas_LixSxEw"
    gsheets_credentials_path: str = "credentials/service_account.json"

    # Dash
    dash_debug: bool = True
    dash_host: str = "0.0.0.0"
    dash_port: int = 8050


# Instancia global default
DEFAULT_CONFIG = AppConfig()
