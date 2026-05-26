"""
config.py — Carga de variables de entorno para el agente de cualificación de leads.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env si existe (útil en desarrollo local)
load_dotenv()


def _require(name: str) -> str:
    """Obtiene una variable de entorno o lanza error claro si falta."""
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(
            f"Variable de entorno requerida no encontrada: {name}\n"
            f"Copia .env.example a .env y rellena los valores."
        )
    return value


# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = _require("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_SHEET_ID: str = _require("GOOGLE_SHEET_ID")

# Las credenciales pueden estar como JSON inline o como path a un fichero
_creds_raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
_creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")

if _creds_raw:
    try:
        GOOGLE_CREDENTIALS: dict = json.loads(_creds_raw)
    except json.JSONDecodeError as e:
        raise EnvironmentError(
            f"GOOGLE_CREDENTIALS_JSON no es JSON válido: {e}"
        )
elif _creds_path:
    creds_file = Path(_creds_path)
    if not creds_file.exists():
        raise EnvironmentError(f"No se encuentra el fichero de credenciales: {_creds_path}")
    GOOGLE_CREDENTIALS: dict = json.loads(creds_file.read_text())
else:
    raise EnvironmentError(
        "Debes definir GOOGLE_CREDENTIALS_JSON (JSON inline) "
        "o GOOGLE_CREDENTIALS_PATH (path al fichero .json)"
    )

# Nombre de la hoja dentro del spreadsheet (por defecto "Leads")
GOOGLE_SHEET_TAB: str = os.getenv("GOOGLE_SHEET_TAB", "Leads")

# ── General ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
