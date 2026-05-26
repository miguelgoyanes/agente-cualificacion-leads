"""
bot/messages.py — Templates de mensajes para respuestas de Telegram.
"""

from services.qualifier import QualificationResult


def format_qualification_response(result: QualificationResult, sheets_ok: bool | None = None) -> str:
    """
    Genera el mensaje de Telegram con la decisión de cualificación.

    Args:
        result: Resultado de la cualificación.
        sheets_ok: True si el log a Sheets funcionó, False si falló, None si aún no se intentó.
    """
    c = result.criteria

    def emoji(val: bool) -> str:
        return "✅" if val else "❌"

    criteria_line = (
        f"{emoji(c.get('tipo_empresa', False))} Tipo empresa  |  "
        f"{emoji(c.get('empleados_minimo', False))} Empleados ≥5  |  "
        f"{emoji(c.get('geografia', False))} Geografía  |  "
        f"{emoji(c.get('interes_automatizacion', False))} Interés auto/IA"
    )

    if result.qualified:
        header = "✅ *Lead CUALIFICADO*"
    else:
        header = "❌ *Lead NO CUALIFICADO*"

    msg = (
        f"{header}\n\n"
        f"{result.reason}\n\n"
        f"📊 {criteria_line}"
    )

    if sheets_ok is True:
        msg += "\n\n📋 _Guardado en registro_"
    elif sheets_ok is False:
        msg += "\n\n⚠️ _Error al guardar en registro_"

    return msg


def format_insufficient_data_response(result: QualificationResult, sheets_ok: bool | None = None) -> str:
    """Mensaje cuando los datos del lead son insuficientes para evaluarlo."""
    missing_str = ""
    if result.missing:
        items = "".join(f"\n  • {campo}" for campo in result.missing)
        missing_str = f"\n\n*Información que falta:*{items}"

    msg = (
        f"❓ *Datos insuficientes*\n\n"
        f"{result.reason}"
        f"{missing_str}\n\n"
        f"_Envía más información sobre el lead para poder evaluarlo._"
    )

    if sheets_ok is True:
        msg += "\n\n📋 _Guardado en registro_"
    elif sheets_ok is False:
        msg += "\n\n⚠️ _Error al guardar en registro_"

    return msg


def format_error_response() -> str:
    """Mensaje de error cuando falla el procesamiento interno."""
    return (
        "⚠️ *Error al procesar el lead*\n\n"
        "No pude analizar los datos en este momento. "
        "Por favor, inténtalo de nuevo en unos segundos.\n\n"
        "_Si el problema persiste, revisa los logs del servidor._"
    )


def format_welcome() -> str:
    """Mensaje de bienvenida al iniciar el bot con /start."""
    return (
        "👋 *Agente de Cualificación de Leads — Orbyn*\n\n"
        "Envíame los datos de un lead en texto libre y analizaré si encaja con nuestro ICP.\n\n"
        "*Ejemplo:*\n"
        "_\"Empresa de consultoría, 15 empleados, Madrid, quieren automatizar su proceso de ventas.\"_\n\n"
        "📋 *Criterios ICP:*\n"
        "• Empresa de servicios o consultoría\n"
        "• Mínimo 5 empleados\n"
        "• España o Latinoamérica\n"
        "• Interés en automatización o IA"
    )


def format_help() -> str:
    """Mensaje de ayuda."""
    return (
        "ℹ️ *Cómo usar este bot*\n\n"
        "Simplemente envía los datos del lead en texto libre. No hace falta un formato especial.\n\n"
        "*Ejemplos de mensajes válidos:*\n"
        "• _\"Agencia de marketing digital en Buenos Aires, 8 personas, buscan herramientas de IA\"_\n"
        "• _\"Consultoría de RRHH, Madrid, 12 empleados, interés en automatizar onboarding\"_\n"
        "• _\"Startup de e-commerce en EE.UU.\"_\n\n"
        "El bot analizará los datos y te dirá si el lead está cualificado o no, con el razonamiento."
    )


