# Balance de Masas Cu/H₂SO₄ — Planta Lix/SX/EW

## Proyecto

App en Dash (Python) para calcular el balance mensual de cobre y ácido sulfúrico en una cadena Lixiviación (pilas dinámicas) → SX (2E+1S) → EW. Incluye un módulo detallado de balance por franja horizontal con subdivisión en módulos de riego.

## Stack

- **Framework**: Dash + Dash Bootstrap Components
- **Gráficos**: Plotly
- **Data**: Pandas
- **Persistencia**: Google Sheets (gspread + google-auth)
- **Reportes**: openpyxl (Excel) + reportlab (PDF)
- **Deploy**: Render (gunicorn)
- **Python**: 3.11+

## Estructura del Proyecto

```
balance-masas-app/
├── CLAUDE.md
├── app.py                          # Entry point Dash
├── config.py                       # Settings, factores estequiométricos default
├── requirements.txt
├── Procfile
├── assets/
│   └── styles.css
├── modules/
│   ├── __init__.py
│   ├── data_loader.py              # Carga y validación Excel/CSV
│   ├── leaching.py                 # Cálculos LIX globales
│   ├── solvent_extraction.py       # Cálculos SX (2E+1S)
│   ├── electrowinning.py           # Cálculos EW
│   ├── mass_balance.py             # Balance global Cu + Ácido
│   ├── sheets_backend.py           # CRUD Google Sheets
│   ├── dashboard.py                # Layout y callbacks Dash principales
│   └── reports.py                  # Generación Excel/PDF
├── modules/heap_franja/
│   ├── __init__.py
│   ├── models.py                   # Pad, Ciclo, Franja, Modulo, Ruteo, datos diarios
│   ├── copper_balance.py           # Balance Cu DIRECTO por franja
│   ├── acid_balance.py             # Descomposición ácido por componente
│   ├── weighted_input.py           # Entrada ponderada desde módulos a franja
│   ├── leach_ratio.py              # RL total/refino/ILS/por fuente
│   ├── irrigation.py               # Gestión de ruteo, transiciones refino↔ILS
│   ├── routing_graph.py            # Grafo de flujo entre franjas (Sankey)
│   ├── gangue_proxies.py           # Proxys Fe/Cl⁻/SiO₂/Mn + factores DRX
│   ├── kinetics.py                 # Curvas Rec vs RL, proyección cut-off
│   ├── holdup.py                   # Corrección holdup por franja
│   ├── reconciliation.py           # Balance soluciones vs sólidos
│   ├── aggregation.py              # Franja → ciclo → pad
│   ├── lifecycle.py                # Estados: apilando→regando→drenando→desarmado
│   ├── dashboard_pad.py            # Vista mapa pad + Sankey
│   ├── dashboard_franja.py         # Vistas balance + RL + riego
│   ├── dashboard_compare.py        # Vistas comparativas entre franjas
│   ├── validators.py               # Validaciones + alertas
│   └── config.py                   # Factores estequiométricos editables
├── templates/
│   └── template_input.xlsx         # Template para carga de datos
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures con datos sintéticos
│   ├── test_models.py
│   ├── test_copper_balance.py
│   ├── test_acid_balance.py
│   ├── test_weighted_input.py
│   ├── test_leach_ratio.py
│   └── test_irrigation.py
├── data/
│   └── synthetic/                  # Datos sintéticos para desarrollo
│       ├── pad_metadata.csv
│       ├── riego_diario.csv
│       └── pls_diario.csv
└── docs/
    ├── plan_balance_masas_lix_sx_ew.md
    ├── modulo_balance_pad_horizontal_v4.md
    └── README_operacional.md
```

## Convenciones de Código

- Python 3.11+, type hints en todas las funciones
- Dataclasses para modelos de datos (no Pydantic por simplicidad)
- Docstrings en español (el dominio es minería de cobre en Chile/Perú)
- Tests con pytest, fixtures con datos sintéticos realistas
- Nombres de variables en español para dominio (tonelaje_t, ley_cu_soluble_pct)
- Nombres de funciones en inglés (calculate_recovery, get_weighted_input)
- Cálculos siempre en kg para masas, m³ para volúmenes, g/L para concentraciones

## Contexto del Dominio

### Geometría del Pad
- Franjas HORIZONTALES en el mismo plano (NO lifts verticales)
- Siempre single-lift (una sola capa de mineral)
- Cada franja se subdivide en N módulos de riego
- El PLS se colecta POR FRANJA (no por módulo)
- El módulo es unidad de gestión de riego, la franja es unidad de balance

### Tipos de Solución
- **Refino**: solución de retorno de SX, baja en Cu, con ácido libre
- **ILS**: Intermediate Leach Solution, PLS de una franja usado como riego de otra
- El ruteo refino/ILS es CONFIGURABLE por módulo y variable en el tiempo

### Balance de Cu
- Balance DIRECTO por franja (hay muestreo diario por franja)
- Entrada = suma ponderada de todos los módulos (distintas fuentes)
- Salida = PLS medido de la franja
- Corrección por holdup (humedad residual fija 8-12%)
- Recuperación = Cu extraído / Cu contenido soluble × 100

### Balance de Ácido — Descomposición
1. Ácido por Cu: factor 1.543 kg H₂SO₄/kg Cu
2. Ácido por Fe (ganga): factor ponderado por DRX (goethita 2.63, clorita 2.0)
3. Ácido por Cl⁻ (atacamita): factor 2.8
4. Ácido por SiO₂ (silicatos): factor 1.63
5. Ácido por Mn (óxidos): factor 1.78
6. No asignado: por diferencia

### Proxys Analíticos Disponibles
- Fe total, Fe²⁺, Fe³⁺ (calculado)
- Cl⁻, SiO₂, Mn
- Mineralogía DRX/QEMSCAN por franja

### Criterio de Fin de Riego
- Ratio ácido consumido / Cu producido (cut-off económico definido por usuario)

### Razón de Lixiviación (RL)
- RL = volumen acumulado aplicado / tonelaje (m³/t)
- Segregada por tipo de solución (refino vs ILS) y por fuente de ILS

## Orden de Implementación

### Iteración 1 (ACTUAL) — Motor de cálculo + datos sintéticos
1. `modules/heap_franja/models.py` — Todas las dataclasses
2. `modules/heap_franja/config.py` — Factores estequiométricos default
3. `modules/heap_franja/weighted_input.py` — Entrada ponderada desde módulos
4. `modules/heap_franja/copper_balance.py` — Balance Cu directo por franja
5. `modules/heap_franja/acid_balance.py` — Descomposición ácido
6. `modules/heap_franja/leach_ratio.py` — RL total/refino/ILS
7. `modules/heap_franja/holdup.py` — Corrección holdup
8. `modules/heap_franja/gangue_proxies.py` — Cálculo de proxys
9. `tests/conftest.py` — Datos sintéticos: 1 pad, 1 ciclo, 3 franjas, 2-3 módulos c/u, 90 días
10. Tests unitarios para cada módulo
11. `data/synthetic/` — CSVs con datos sintéticos generados

### Iteración 2 — Dashboard
12. `modules/heap_franja/irrigation.py` — Ruteo y transiciones
13. `modules/heap_franja/routing_graph.py` — Grafo Sankey
14. `modules/heap_franja/dashboard_pad.py` — Mapa del pad
15. `modules/heap_franja/dashboard_franja.py` — Balance + RL + riego
16. `modules/heap_franja/dashboard_compare.py` — Comparativas
17. `app.py` — Integración Dash

### Iteración 3 — Módulos principales Lix/SX/EW
18. `modules/leaching.py`, `solvent_extraction.py`, `electrowinning.py`
19. `modules/mass_balance.py`
20. `modules/dashboard.py`

### Iteración 4 — Persistencia + Reportes + Deploy
21. `modules/sheets_backend.py`
22. `modules/data_loader.py`
23. `modules/reports.py`
24. Configuración de deploy en Render

## Reglas para Claude Code

- Siempre corre `pytest` después de crear o modificar un módulo
- Si un test falla, corrígelo antes de avanzar al siguiente módulo
- Genera datos sintéticos REALISTAS (leyes Cu entre 0.3-1.2%, recuperaciones 50-75%, concentraciones PLS 1-6 g/L Cu)
- Los factores estequiométricos deben ser configurables, nunca hardcodeados
- Cada función debe tener al menos un test
- Usa logging (no print) para mensajes de diagnóstico
