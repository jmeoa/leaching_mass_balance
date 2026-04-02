"""
Configuración compartida para el motor de balance por franja.

La app principal ya define los factores y parámetros por defecto en
`config.py`; este módulo simplemente los reexporta para mantener el
namespace de `modules.heap_franja` autocontenido.
"""

from config import (  # noqa: F401
    AppConfig,
    DEFAULT_CONFIG,
    FactoresEstequiometricos,
    ParametrosDefault,
)

__all__ = [
    "AppConfig",
    "DEFAULT_CONFIG",
    "FactoresEstequiometricos",
    "ParametrosDefault",
]
