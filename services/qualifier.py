"""
services/qualifier.py — Lógica de cualificación de leads usando Groq (Llama 3.3).

ICP (Ideal Customer Profile) de Orbyn:
  1. Tipo de empresa: servicios o consultoría
  2. Tamaño: mínimo 5 empleados
  3. Geografía: España o Latinoamérica
  4. Interés: automatización o IA
"""

import json
import logging
import time
from dataclasses import dataclass, field

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

# Cliente Groq — inicializado una sola vez al importar el módulo
_client = Groq(api_key=GROQ_API_KEY)

# Configuración de reintentos
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # segundos — backoff exponencial: 2s, 4s, 8s


@dataclass
class QualificationResult:
    """Resultado estructurado de la cualificación de un lead."""
    qualified: bool
    decision: str          # "CUALIFICADO" | "NO CUALIFICADO" | "DATOS_INSUFICIENTES"
    reason: str            # 2-3 líneas de razonamiento
    criteria: dict         # {tipo_empresa, empleados_minimo, geografia, interes_automatizacion}
    raw_input: str         # Texto original del lead
    missing: list = field(default_factory=list)  # Campos ausentes (solo en DATOS_INSUFICIENTES)


# ── System prompt ─────────────────────────────────────────────────────────────
# El input del usuario se inyecta como dato (entre <lead_data>), nunca como
# instrucción directa. Esto previene prompt injection.

SYSTEM_PROMPT = """Eres un agente de cualificación de leads B2B para una empresa de automatización e IA llamada Orbyn.

Tu tarea es analizar la información de un lead recibida en texto libre y determinar si encaja con el siguiente ICP (Ideal Customer Profile):

ICP DE ORBYN:
1. TIPO DE EMPRESA: Debe ser una empresa de servicios o consultoría (NO e-commerce, manufactura, retail, SaaS técnico propio, etc.)
2. TAMAÑO: Mínimo 5 empleados (si no se menciona el número, debes inferirlo del contexto; si es imposible determinarlo, considera que NO cumple)
3. GEOGRAFÍA: Debe estar en España o en Latinoamérica (LATAM). No cualificar empresas de EE.UU., Europa fuera de España, Asia, etc.
4. INTERÉS: Debe mostrar interés explícito o implícito en automatización de procesos, inteligencia artificial, o digitalización de operaciones.

CASO ESPECIAL — DATOS INSUFICIENTES:
Si el mensaje es tan escaso que no puedes evaluar 2 o más criterios (por ejemplo "empresa en Madrid" sin más información), responde con decision "DATOS_INSUFICIENTES" e indica qué datos concretos faltan.

INSTRUCCIONES:
- Analiza el texto del lead de forma objetiva y extrae la información disponible.
- Si un criterio no puede determinarse por falta de información, márcalo como false.
- Sé estricto: un lead solo es CUALIFICADO si cumple los 4 criterios.
- El motivo debe ser concreto y específico, no genérico. Menciona los datos reales del lead.
- Responde ÚNICAMENTE con un JSON válido, sin texto adicional, sin markdown, sin explicaciones fuera del JSON.

FORMATO DE RESPUESTA — Lead evaluable:
{
  "qualified": true o false,
  "decision": "CUALIFICADO" o "NO CUALIFICADO",
  "reason": "2-3 líneas explicando el razonamiento con datos concretos del lead",
  "missing": [],
  "criteria": {
    "tipo_empresa": true o false,
    "empleados_minimo": true o false,
    "geografia": true o false,
    "interes_automatizacion": true o false
  }
}

FORMATO DE RESPUESTA — Datos insuficientes:
{
  "qualified": false,
  "decision": "DATOS_INSUFICIENTES",
  "reason": "Explica qué información falta y por qué es necesaria para evaluar el lead",
  "missing": ["tipo de empresa", "número de empleados"],
  "criteria": {
    "tipo_empresa": false,
    "empleados_minimo": false,
    "geografia": false,
    "interes_automatizacion": false
  }
}"""


def qualify_lead(lead_text: str) -> QualificationResult:
    """
    Envía el texto del lead a Groq (Llama) y devuelve un QualificationResult.
    Reintenta automáticamente hasta MAX_RETRIES veces con backoff exponencial.

    Args:
        lead_text: Texto libre con los datos del lead recibido por Telegram.

    Returns:
        QualificationResult con la decisión y el razonamiento.

    Raises:
        ValueError: Si la respuesta no puede parsearse como JSON válido.
        Exception: Si todos los reintentos fallan.
    """
    logger.info("Cualificando lead: %s", lead_text[:100])

    # El input del usuario va entre delimitadores XML — nunca como instrucción directa
    user_message = f"""Analiza este lead y responde con el JSON requerido:

<lead_data>
{lead_text}
</lead_data>"""

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )

            raw_response = response.choices[0].message.content.strip()
            logger.debug("Respuesta Groq (intento %d): %s", attempt, raw_response)

            parsed = _parse_json_response(raw_response)

            return QualificationResult(
                qualified=parsed["qualified"],
                decision=parsed["decision"],
                reason=parsed["reason"],
                criteria=parsed["criteria"],
                raw_input=lead_text,
                missing=parsed.get("missing", []),
            )

        except ValueError:
            # Error de parsing — no tiene sentido reintentar
            raise

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt  # 2s, 4s, 6s
                logger.warning(
                    "Intento %d/%d fallido, reintentando en %ds: %s",
                    attempt, MAX_RETRIES, delay, e,
                )
                time.sleep(delay)
            else:
                logger.error("Todos los reintentos agotados: %s", e)

    raise last_error


def _parse_json_response(text: str) -> dict:
    """
    Parsea la respuesta JSON y valida que tenga todos los campos requeridos.
    Lanza ValueError si el JSON es inválido o faltan campos.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("JSON inválido: %s\nTexto: %s", e, text)
        raise ValueError(f"Respuesta JSON inválida: {e}")

    required_keys = {"qualified", "decision", "reason", "criteria"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Faltan campos en la respuesta: {missing}")

    required_criteria = {"tipo_empresa", "empleados_minimo", "geografia", "interes_automatizacion"}
    missing_criteria = required_criteria - set(data.get("criteria", {}).keys())
    if missing_criteria:
        raise ValueError(f"Faltan criterios en la respuesta: {missing_criteria}")

    return data
