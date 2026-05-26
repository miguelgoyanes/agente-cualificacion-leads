"""
services/sheets.py — Logging de leads cualificados en Google Sheets.

Columnas del spreadsheet:
  A: Fecha/Hora
  B: Datos Lead (texto recibido)
  C: Decisión (CUALIFICADO / NO CUALIFICADO)
  D: Motivo
  E: Tipo Empresa ✅/❌
  F: Empleados Mínimo ✅/❌
  G: Geografía ✅/❌
  H: Interés Automatización ✅/❌
  I: Usuario Telegram
  J: Chat ID
"""

import logging
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, GOOGLE_SHEET_ID, GOOGLE_SHEET_TAB
from services.qualifier import QualificationResult

logger = logging.getLogger(__name__)

# Scopes mínimos necesarios
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# Cabeceras de la hoja (se crean automáticamente si la hoja está vacía)
_HEADERS = [
    "Fecha/Hora",
    "Datos Lead",
    "Decisión",
    "Motivo",
    "Tipo Empresa",
    "Empleados ≥5",
    "Geografía",
    "Interés Auto/IA",
    "Usuario Telegram",
    "Chat ID",
]

# Cliente gspread — se inicializa de forma lazy (una sola vez)
_client: gspread.Client | None = None
_worksheet: gspread.Worksheet | None = None


def _get_worksheet() -> gspread.Worksheet:
    """Devuelve el worksheet cacheado, creando la conexión si no existe."""
    global _client, _worksheet

    if _worksheet is not None:
        return _worksheet

    logger.info("Conectando a Google Sheets...")
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=_SCOPES)
    _client = gspread.authorize(creds)

    spreadsheet = _client.open_by_key(GOOGLE_SHEET_ID)

    # Obtener o crear la pestaña
    try:
        _worksheet = spreadsheet.worksheet(GOOGLE_SHEET_TAB)
        logger.info("Hoja '%s' encontrada.", GOOGLE_SHEET_TAB)
    except gspread.WorksheetNotFound:
        logger.info("Creando hoja '%s'...", GOOGLE_SHEET_TAB)
        _worksheet = spreadsheet.add_worksheet(
            title=GOOGLE_SHEET_TAB, rows=1000, cols=len(_HEADERS)
        )

    # Añadir cabeceras si la hoja está vacía
    if _worksheet.row_count == 0 or not _worksheet.row_values(1):
        _worksheet.append_row(_HEADERS, value_input_option="USER_ENTERED")
        logger.info("Cabeceras creadas en la hoja.")

    return _worksheet


def _bool_to_emoji(value: bool) -> str:
    return "✅" if value else "❌"


def log_lead(
    result: QualificationResult,
    telegram_username: str = "",
    chat_id: str = "",
) -> None:
    """
    Añade una fila con los datos del lead y la decisión al Google Sheet.

    Args:
        result: Resultado de la cualificación.
        telegram_username: @username del usuario de Telegram (puede estar vacío).
        chat_id: ID del chat de Telegram.
    """
    try:
        ws = _get_worksheet()

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        row = [
            now,
            result.raw_input,
            result.decision,
            result.reason,
            _bool_to_emoji(result.criteria.get("tipo_empresa", False)),
            _bool_to_emoji(result.criteria.get("empleados_minimo", False)),
            _bool_to_emoji(result.criteria.get("geografia", False)),
            _bool_to_emoji(result.criteria.get("interes_automatizacion", False)),
            telegram_username or "—",
            str(chat_id),
        ]

        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Lead logueado en Google Sheets: %s", result.decision)

    except Exception as e:
        # El fallo del log NO debe interrumpir la respuesta al usuario
        logger.error("Error al loguear en Google Sheets: %s", e, exc_info=True)
