"""Persistencia incremental en Google Sheets con fallback local."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from config import DEFAULT_CONFIG

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:  # pragma: no cover - depende del entorno
    gspread = None
    Credentials = None


LOCAL_STORE_DIR = Path(__file__).resolve().parents[1] / "data" / "local_store"
LOCAL_STORE_FILE = LOCAL_STORE_DIR / "monthly_input.csv"


class BaseSheetsBackend:
    """Interfaz mínima para persistencia mensual."""

    def append_month(self, periodo: str, data: dict) -> None:
        raise NotImplementedError

    def get_history(self, desde: Optional[str] = None, hasta: Optional[str] = None) -> pd.DataFrame:
        raise NotImplementedError

    def update_month(self, periodo: str, data: dict) -> None:
        raise NotImplementedError

    def get_latest_inventory(self) -> list:
        raise NotImplementedError


class LocalSheetsBackend(BaseSheetsBackend):
    """Persistencia local tipo stub cuando no hay credenciales."""

    def __init__(self) -> None:
        LOCAL_STORE_DIR.mkdir(parents=True, exist_ok=True)

    def _read(self) -> pd.DataFrame:
        if not LOCAL_STORE_FILE.exists():
            return pd.DataFrame()
        df = pd.read_csv(LOCAL_STORE_FILE)
        if "periodo" in df.columns:
            df["periodo"] = pd.to_datetime(df["periodo"])
        return df

    def _write(self, df: pd.DataFrame) -> None:
        LOCAL_STORE_DIR.mkdir(parents=True, exist_ok=True)
        df = df.copy()
        if "periodo" in df.columns:
            df["periodo"] = pd.to_datetime(df["periodo"]).dt.strftime("%Y-%m-%d")
        df.to_csv(LOCAL_STORE_FILE, index=False)

    def append_month(self, periodo: str, data: dict) -> None:
        df = self._read()
        row = pd.DataFrame([{**data, "periodo": pd.Timestamp(periodo)}])
        df = pd.concat([df, row], ignore_index=True)
        df = df.drop_duplicates(subset=["periodo"], keep="last").sort_values("periodo")
        self._write(df)

    def get_history(self, desde: Optional[str] = None, hasta: Optional[str] = None) -> pd.DataFrame:
        df = self._read()
        if df.empty:
            return df
        if desde:
            df = df[df["periodo"] >= pd.Timestamp(desde)]
        if hasta:
            df = df[df["periodo"] <= pd.Timestamp(hasta)]
        return df.sort_values("periodo").reset_index(drop=True)

    def update_month(self, periodo: str, data: dict) -> None:
        self.append_month(periodo, data)

    def get_latest_inventory(self) -> list:
        df = self._read()
        if df.empty or "pilas_activas_inventario" not in df.columns:
            return []
        latest = df.sort_values("periodo").iloc[-1]["pilas_activas_inventario"]
        if isinstance(latest, list):
            return latest
        try:
            return json.loads(latest)
        except Exception:
            return []


class GoogleSheetsBackend(BaseSheetsBackend):
    """Backend real de Google Sheets."""

    def __init__(self, spreadsheet_name: str | None = None, credentials_path: str | None = None) -> None:
        if gspread is None or Credentials is None:
            raise RuntimeError("Google Sheets backend no disponible en este entorno")
        spreadsheet_name = spreadsheet_name or DEFAULT_CONFIG.gsheets_spreadsheet_name
        credentials_path = credentials_path or DEFAULT_CONFIG.gsheets_credentials_path
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        client = gspread.authorize(creds)
        self.spreadsheet = client.open(spreadsheet_name)
        self.worksheet = self.spreadsheet.worksheet("data_mensual")

    def append_month(self, periodo: str, data: dict) -> None:
        row = {**data, "periodo": periodo}
        self.worksheet.append_row(list(row.values()), value_input_option="USER_ENTERED")

    def get_history(self, desde: Optional[str] = None, hasta: Optional[str] = None) -> pd.DataFrame:
        rows = self.worksheet.get_all_records()
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["periodo"] = pd.to_datetime(df["periodo"])
        if desde:
            df = df[df["periodo"] >= pd.Timestamp(desde)]
        if hasta:
            df = df[df["periodo"] <= pd.Timestamp(hasta)]
        return df.sort_values("periodo").reset_index(drop=True)

    def update_month(self, periodo: str, data: dict) -> None:
        df = self.get_history()
        row_index = None
        for idx, row in enumerate(df.to_dict("records"), start=2):
            if pd.Timestamp(row["periodo"]).strftime("%Y-%m") == pd.Timestamp(periodo).strftime("%Y-%m"):
                row_index = idx
                break
        if row_index is None:
            self.append_month(periodo, data)
            return
        values = [{**data, "periodo": periodo}[column] for column in df.columns]
        self.worksheet.update(f"A{row_index}:{chr(64 + len(values))}{row_index}", [values])

    def get_latest_inventory(self) -> list:
        df = self.get_history()
        if df.empty:
            return []
        latest = df.sort_values("periodo").iloc[-1]["pilas_activas_inventario"]
        if isinstance(latest, list):
            return latest
        return json.loads(latest)


def get_backend() -> BaseSheetsBackend:
    """Entrega Google Sheets si está configurado; si no, usa fallback local."""
    credentials_path = Path(DEFAULT_CONFIG.gsheets_credentials_path)
    if credentials_path.exists() and gspread is not None and Credentials is not None:
        try:
            return GoogleSheetsBackend()
        except Exception:
            return LocalSheetsBackend()
    return LocalSheetsBackend()
