# README Operacional

## Arquitectura actual

La aplicación corre sobre:

- `FastAPI` para la API y la lógica de backend
- `React + Vite` para la interfaz web
- `Pandas` para cálculo mensual y analítica de heap/franja
- `Google Sheets` opcional, con fallback local en CSV
- `Render` para despliegue

## Estructura operativa

- `app.py`: runner local para levantar la app completa en desarrollo
- `backend/api/main.py`: API principal FastAPI
- `backend/core/services.py`: orquestación entre API, motor de cálculo y reportes
- `frontend/`: aplicación React compilada a `frontend/dist`
- `modules/`: motor mensual LIX/SX/EW, carga, persistencia y reportes
- `modules/heap_franja/`: motor detallado por pad, ciclo, franja y módulo

## Desarrollo local

### Backend

```bash
cd balance-masas-app
python3 -m pip install -r requirements.txt
python3 app.py
```

La API queda disponible en `http://127.0.0.1:8050`.

### Frontend

```bash
cd balance-masas-app/frontend
npm install
npm run dev
```

El frontend usa proxy a `/api` contra `http://127.0.0.1:8050`.

## Build de producción

```bash
cd balance-masas-app/frontend
npm run build
```

El bundle generado en `frontend/dist` es servido por FastAPI.

## Tests

```bash
cd balance-masas-app
python3 -m pytest -q
```

## Flujo operacional

1. Cargar un archivo mensual Excel/CSV desde la vista `Carga`.
2. Previsualizar y validar columnas/valores.
3. Procesar y persistir el mes en backend local o Google Sheets.
4. Revisar el resumen mensual LIX/SX/EW en `Resumen`.
5. Analizar el pad completo en `Heap / Pad`.
6. Analizar curvas y alertas por franja en `Franja`.
7. Descargar reportes Excel/PDF desde `Reportes`.

## Deploy en Render

- Root directory: `balance-masas-app`
- Build command: `python3 -m pip install -r requirements.txt`
- Start command:

```bash
python3 -m gunicorn backend.api.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

## Persistencia

- Si existen credenciales válidas de Google Sheets, la app usa `GoogleSheetsBackend`.
- Si no existen, cae automáticamente a `data/local_store/monthly_input.csv`.
