# Plan de Implementación: Balance de Masas Cu/H₂SO₄ — Planta Lix/SX/EW

## 1. Visión General

App en **Dash (Python)** para calcular el balance mensual de cobre y ácido sulfúrico en una cadena Lixiviación → SX (2E+1S) → EW, con:

- **Input**: Carga de archivos Excel/CSV
- **Persistencia**: Google Sheets como backend incremental
- **Output**: Dashboard interactivo + reportes descargables (Excel/PDF)

---

## 2. Arquitectura Modular

```
┌─────────────────────────────────────────────────────────┐
│                      DASH APP                           │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│  Módulo  │  Módulo  │  Módulo  │  Módulo  │   Módulo    │
│  CARGA   │   LIX    │    SX    │    EW    │  REPORTES   │
│  (I/O)   │          │ (2E+1S)  │          │             │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│              CAPA DE CÁLCULO (Engine)                    │
├─────────────────────────────────────────────────────────┤
│          PERSISTENCIA (Google Sheets API)                │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Módulos Detallados

### 3.1 Módulo de Carga (I/O)

**Archivo**: `modules/data_loader.py`

**Funcionalidad**:
- Upload de Excel/CSV vía `dcc.Upload`
- Validación de columnas esperadas (template estándar)
- Preview de datos antes de confirmar carga
- Mapeo flexible de columnas (por si el formato varía)

**Template de input esperado (una fila por mes)**:

| Campo | Unidad | Etapa |
|-------|--------|-------|
| `periodo` | YYYY-MM | General |
| `mineral_alimentado_ton` | t | LIX |
| `ley_cu_alimentada` | % Cu | LIX |
| `vol_pls_m3` | m³ | LIX |
| `cu_pls_gpl` | g/L Cu | LIX |
| `acid_pls_gpl` | g/L H₂SO₄ | LIX |
| `vol_refino_m3` | m³ | LIX |
| `cu_refino_gpl` | g/L Cu | LIX |
| `acid_refino_gpl` | g/L H₂SO₄ | LIX |
| `vol_acuoso_cargado_m3` | m³ | SX |
| `cu_acuoso_cargado_gpl` | g/L Cu | SX |
| `vol_electrolito_rico_m3` | m³ | SX |
| `cu_electrolito_rico_gpl` | g/L Cu | SX |
| `acid_electrolito_rico_gpl` | g/L H₂SO₄ | SX |
| `vol_electrolito_pobre_m3` | m³ | SX |
| `cu_electrolito_pobre_gpl` | g/L Cu | SX |
| `acid_electrolito_pobre_gpl` | g/L H₂SO₄ | SX |
| `catodos_ton` | t Cu fino | EW |
| `eficiencia_corriente` | % | EW |
| `acid_makeup_ton` | t H₂SO₄ | General |
| `pilas_activas_inventario` | JSON/detalle | LIX |

### 3.2 Módulo Lixiviación (LIX)

**Archivo**: `modules/leaching.py`

**Cálculos clave**:
- **Cu alimentado a pilas** = mineral_ton × ley_cu / 100
- **Cu extraído en PLS** = vol_PLS × Cu_PLS / 1000
- **Cu en refino (no extraído)** = vol_refino × Cu_refino / 1000
- **Recuperación LIX** = Cu extraído / Cu alimentado × 100
- **Inventario Cu en pilas** (acumulativo):
  - `inv_pilas[t] = inv_pilas[t-1] + Cu_alimentado[t] - Cu_extraído[t]`
  - Representa el cobre "por recuperar" en pilas activas
- **Consumo ácido LIX** = (vol_refino × acid_refino - vol_PLS × acid_PLS) / 1000
  - Negativo = consumo neto en ganga

**Tracking de pilas dinámicas**:
- Cada pila tiene: `id_pila, fecha_on, fecha_off, ton_mineral, ley_cu, cu_remanente`
- Al hacer OFF → Cu remanente se resta del inventario activo
- Vista de pilas activas vs. agotadas

### 3.3 Módulo SX (2E + 1S)

**Archivo**: `modules/solvent_extraction.py`

**Cálculos clave**:
- **Cu transferido en extracción** = (Cu_PLS - Cu_refino) × vol_acuoso
- **Cu transferido en stripping** = (Cu_elec_rico - Cu_elec_pobre) × vol_electrolito
- **Recuperación SX** = Cu en electrolito rico / Cu en PLS × 100
- **Balance SX** = Cu entrada acuosa - Cu salida acuosa - Cu transferido a orgánico
- **Transfer ácido SX**:
  - Ácido generado en extracción (por cada mol Cu extraído → 1 mol H₂SO₄ liberado)
  - Ácido consumido en stripping

**Indicadores**:
- Relación O/A (orgánico/acuoso)
- Selectividad (si hay datos de impurezas)
- Delta Cu entre etapas

### 3.4 Módulo EW

**Archivo**: `modules/electrowinning.py`

**Cálculos clave**:
- **Producción de cátodos** = dato directo (ton Cu)
- **Eficiencia de corriente** = dato directo o calculada
- **Cu depositado** = catodos_ton
- **Ácido generado en EW**:
  - Estequiométrico: ~1.54 kg H₂SO₄ / kg Cu depositado
  - `acid_generado_ew = catodos_ton × 1.54`
- **Recuperación EW** = Cu cátodos / Cu en electrolito rico × 100

### 3.5 Módulo Balance Global

**Archivo**: `modules/mass_balance.py`

**Balance de Cobre (mensual)**:
```
Cu_entrada    = Cu alimentado a pilas
Cu_salida     = Cu cátodos
Cu_inventario = Δ inventario pilas + Δ inventario soluciones
Cu_pérdidas   = Cu_entrada - Cu_salida - Δ_inventario  (por diferencia)

Recuperación global = Cu_cátodos / Cu_alimentado × 100
```

**Balance de Ácido (mensual)**:
```
Ácido_entrada  = acid_makeup + acid_generado_EW + acid_generado_SX_extracción
Ácido_salida   = acid_consumido_LIX + acid_consumido_SX_stripping
Ácido_neto     = Ácido_entrada - Ácido_salida
Consumo_neto   = acid_makeup / catodos_ton  [kg H₂SO₄ / kg Cu]
```

### 3.6 Módulo Persistencia (Google Sheets)

**Archivo**: `modules/sheets_backend.py`

**Estructura de hojas**:

| Hoja | Contenido |
|------|-----------|
| `data_mensual` | Datos crudos cargados por mes |
| `balance_cu` | Resultados balance Cu calculados |
| `balance_acid` | Resultados balance ácido calculados |
| `inventario_pilas` | Tracking acumulativo de pilas |
| `kpis_historicos` | Serie de tiempo de indicadores |

**Operaciones**:
- `append_month(periodo, data)` — agrega un mes nuevo
- `get_history(desde, hasta)` — lee rango histórico
- `update_month(periodo, data)` — corrige un mes existente
- `get_latest_inventory()` — último inventario acumulado

**Librería**: `gspread` + credenciales de servicio (Service Account)

### 3.7 Módulo Dashboard

**Archivo**: `modules/dashboard.py`

**Pestañas**:

1. **Carga de Datos** — Upload + preview + validación + botón "Procesar"
2. **Balance Mensual** — Tabla resumen del mes seleccionado (Cu + Ácido)
3. **Tendencias** — Gráficos de línea (Plotly):
   - Producción de cátodos vs. Cu alimentado
   - Recuperación por etapa (LIX, SX, EW, Global)
   - Consumo neto de ácido (kg/kg Cu)
   - Inventario Cu en pilas
4. **Inventario de Pilas** — Estado actual de pilas activas/agotadas
5. **Reportes** — Generación y descarga de Excel/PDF

### 3.8 Módulo Reportes

**Archivo**: `modules/reports.py`

- **Excel**: `openpyxl` — reporte mensual con hojas por etapa + resumen
- **PDF**: `reportlab` — reporte ejecutivo con gráficos embebidos
- Descarga vía `dcc.Download`

---

## 4. Estructura del Proyecto

```
balance-masas-app/
├── app.py                      # Entry point Dash
├── config.py                   # Configuración (GSheets credentials, etc.)
├── requirements.txt
├── assets/
│   └── styles.css              # CSS personalizado
├── modules/
│   ├── __init__.py
│   ├── data_loader.py          # Carga y validación Excel/CSV
│   ├── leaching.py             # Cálculos LIX + inventario pilas
│   ├── solvent_extraction.py   # Cálculos SX (2E+1S)
│   ├── electrowinning.py       # Cálculos EW
│   ├── mass_balance.py         # Balance global Cu + Ácido
│   ├── sheets_backend.py       # CRUD Google Sheets
│   ├── dashboard.py            # Layout y callbacks Dash
│   └── reports.py              # Generación Excel/PDF
├── templates/
│   └── template_input.xlsx     # Template para carga de datos
├── credentials/
│   └── service_account.json    # Credenciales GSheets (gitignored)
└── tests/
    ├── test_leaching.py
    ├── test_sx.py
    ├── test_ew.py
    └── test_balance.py
```

---

## 5. Plan de Implementación (Fases)

### Fase 1 — Fundamentos (Semana 1-2)
- [ ] Setup proyecto + dependencias
- [ ] Módulo `data_loader` con validación
- [ ] Módulo `sheets_backend` (conexión + CRUD básico)
- [ ] Template Excel de input
- [ ] Tests unitarios de carga

### Fase 2 — Motor de Cálculo (Semana 3-4)
- [ ] `leaching.py` con inventario de pilas dinámicas
- [ ] `solvent_extraction.py` con balance 2E+1S
- [ ] `electrowinning.py`
- [ ] `mass_balance.py` (integración global Cu + Ácido)
- [ ] Tests unitarios con datos sintéticos

### Fase 3 — Dashboard (Semana 5-6)
- [ ] Layout Dash con pestañas
- [ ] Callbacks de carga → cálculo → visualización
- [ ] Gráficos Plotly de tendencias
- [ ] Vista de inventario de pilas
- [ ] Integración con Google Sheets (lectura histórica)

### Fase 4 — Reportes + Deploy (Semana 7-8)
- [ ] Generación de reporte Excel
- [ ] Generación de reporte PDF
- [ ] Deploy en Render (free tier)
- [ ] Documentación de uso
- [ ] Template + datos de ejemplo

---

## 6. Dependencias Principales

```
dash>=2.14
dash-bootstrap-components
plotly>=5.18
pandas>=2.0
openpyxl
gspread
google-auth
reportlab
gunicorn
```

---

## 7. Supuestos y Notas

- **Recuperación por etapa**: Se calcula LIX, SX y EW por separado, más una global
- **Ácido**: Balance considera consumo LIX + generación EW (1.54 kg/kg Cu) + makeup. Se puede extender a purgas/ripios si es necesario
- **Pilas dinámicas**: Cada pila se trackea individualmente (on/off/agotada). El inventario de Cu en pilas es la suma de Cu remanente en pilas activas
- **Google Sheets** actúa como base de datos ligera; si el volumen crece mucho (>1000 filas), se puede migrar a SQLite/PostgreSQL sin cambiar la lógica de cálculo
- **Sin autenticación** en v1; se puede agregar después con Flask-Login si se despliega para múltiples usuarios
