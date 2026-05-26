"""
main.py — Punto de entrada del agente de cualificación de leads.

Arranca el bot de Telegram en modo polling (sin necesidad de HTTPS/dominio).
Para producción en VPS con dominio, se puede cambiar a webhook.
"""

import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

import config  # Valida todas las variables de entorno al importar
from bot.handlers import (
    help_handler,
    lead_handler,
    start_handler,
    unknown_command_handler,
)

# ── Configurar logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Construye la app de Telegram y arranca el polling."""
    logger.info("Iniciando Agente de Cualificación de Leads — Orbyn")
    logger.info("Modelo LLM: %s (Groq)", config.GROQ_MODEL)

    # Construir la aplicación
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # ── Registrar handlers ────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Handler principal: cualquier mensaje de texto (que no sea comando)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, lead_handler)
    )

    # Comandos desconocidos
    app.add_handler(
        MessageHandler(filters.COMMAND, unknown_command_handler)
    )

    # ── Arrancar polling ──────────────────────────────────────────────────────
    logger.info("Bot arrancado. Esperando mensajes (Ctrl+C para detener)...")
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,   # Ignorar mensajes acumulados mientras estaba offline
    )


if __name__ == "__main__":
    main()
