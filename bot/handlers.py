"""
bot/handlers.py — Handlers de Telegram para el agente de cualificación de leads.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.messages import (
    format_error_response,
    format_help,
    format_insufficient_data_response,
    format_qualification_response,
    format_welcome,
)
from services.qualifier import qualify_lead
from services.sheets import log_lead

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start con el mensaje de bienvenida."""
    await update.message.reply_text(format_welcome(), parse_mode=ParseMode.MARKDOWN)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /help."""
    await update.message.reply_text(format_help(), parse_mode=ParseMode.MARKDOWN)


async def lead_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler principal: recibe el texto del lead, lo cualifica y responde.

    Flujo:
    1. Recibir mensaje → mostrar "analizando..." inmediatamente
    2. Llamar al qualifier (Groq) con reintentos automáticos
    3. Editar el mensaje con la decisión
    4. Loguear en Google Sheets
    5. Editar el mensaje de nuevo añadiendo confirmación del log
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    lead_text = update.message.text.strip()

    logger.info(
        "Nuevo lead de @%s (chat_id=%s): %s",
        user.username or user.first_name,
        chat_id,
        lead_text[:80],
    )

    # Feedback inmediato mientras Groq procesa
    thinking_msg = await update.message.reply_text(
        "🔍 _Analizando lead..._", parse_mode=ParseMode.MARKDOWN
    )

    try:
        # ── 1. Cualificar con Groq (con reintentos automáticos) ───────────────
        result = qualify_lead(lead_text)

        # ── 2. Responder en Telegram (sin estado del log aún) ────────────────
        if result.decision == "DATOS_INSUFICIENTES":
            response_text = format_insufficient_data_response(result)
        else:
            response_text = format_qualification_response(result)

        await thinking_msg.edit_text(response_text, parse_mode=ParseMode.MARKDOWN)

        logger.info(
            "Lead evaluado para @%s: %s",
            user.username or user.first_name,
            result.decision,
        )

        # ── 4. Loguear en Google Sheets ───────────────────────────────────────
        telegram_username = f"@{user.username}" if user.username else user.first_name
        sheets_ok = log_lead(result, telegram_username=telegram_username, chat_id=str(chat_id))

        # ── 5. Editar mensaje añadiendo confirmación del log ──────────────────
        if result.decision == "DATOS_INSUFICIENTES":
            final_text = format_insufficient_data_response(result, sheets_ok=sheets_ok)
        else:
            final_text = format_qualification_response(result, sheets_ok=sheets_ok)

        await thinking_msg.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)

    except ValueError as e:
        logger.error("Error de parsing de respuesta LLM: %s", e)
        await thinking_msg.edit_text(format_error_response(), parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error("Error inesperado en lead_handler: %s", e, exc_info=True)
        await thinking_msg.edit_text(format_error_response(), parse_mode=ParseMode.MARKDOWN)


async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a comandos desconocidos."""
    await update.message.reply_text(
        "❓ Comando no reconocido. Usa /help para ver cómo funciona el bot.",
    )
