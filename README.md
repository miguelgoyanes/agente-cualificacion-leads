# 🤖 Agente de Cualificación de Leads — Orbyn

Bot de Telegram que cualifica leads B2B en tiempo real usando IA (Google Gemini) y registra cada evaluación en Google Sheets.

## ¿Qué hace?

1. **Recibe** datos de un lead en texto libre por Telegram
2. **Analiza** con Gemini si encaja con el ICP de Orbyn
3. **Responde** en el mismo chat con la decisión y el razonamiento
4. **Loguea** cada lead en Google Sheets con fecha, datos, decisión y criterios

### ICP (Ideal Customer Profile) de Orbyn
| Criterio | Requisito |
|---|---|
| Tipo de empresa | Servicios o consultoría |
| Tamaño | Mínimo 5 empleados |
| Geografía | España o Latinoamérica |
| Interés | Automatización o IA |

---

## Stack Técnico

| Componente | Herramienta | Coste |
|---|---|---|
| Bot | python-telegram-bot 21.x | Gratis |
| LLM | Google Gemini 1.5 Flash | **Gratis** (15 RPM, 1M tokens/día) |
| Sheets | gspread + Google Sheets API | Gratis |
| Hosting | Hetzner VPS / cualquier servidor Linux | Variable |

---

## Setup paso a paso

### 1. Crear el bot de Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía `/newbot` y sigue las instrucciones
3. Copia el **token** que te da BotFather

### 2. Obtener API Key de Google Gemini (gratuito)

1. Ve a [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Haz clic en **"Create API Key"**
3. Copia la key generada

> **Límites gratuitos de Gemini 1.5 Flash:** 15 requests/minuto · 1 millón tokens/día · Sin tarjeta de crédito

### 3. Configurar Google Sheets

#### 3a. Crear el proyecto en Google Cloud Console
1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuevo proyecto (p.ej. `orbyn-lead-agent`)
3. Ve a **APIs & Services → Library**
4. Busca y activa **Google Sheets API**

#### 3b. Crear Service Account
1. Ve a **APIs & Services → Credentials**
2. Haz clic en **"Create Credentials → Service Account"**
3. Dale un nombre (p.ej. `lead-agent-bot`)
4. En la página del service account → **Keys → Add Key → JSON**
5. Descarga el fichero JSON (guárdalo como `credentials.json` en el proyecto)

#### 3c. Preparar el Google Sheet
1. Crea un nuevo Google Sheet en [sheets.google.com](https://sheets.google.com)
2. Copia el **ID** de la URL: `docs.google.com/spreadsheets/d/**ESTE_ID**/edit`
3. Haz clic en **Compartir** y añade el email del service account (está en el JSON, campo `client_email`)
4. Dale permiso de **Editor**

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```env
TELEGRAM_BOT_TOKEN=123456:ABCdef...
GEMINI_API_KEY=AIzaSy...
GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
GOOGLE_CREDENTIALS_PATH=credentials.json
```

### 5. Instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 6. Ejecutar localmente (para pruebas)

```bash
python main.py
```

---

## Deploy en Hetzner VPS (producción)

### Clonar y configurar

```bash
# Conectarte al VPS
ssh usuario@tu-ip-hetzner

# Clonar el repositorio
git clone https://github.com/tu-usuario/agente-cualificacion-leads.git
cd agente-cualificacion-leads

# Entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
nano .env  # Rellenar con los valores reales

# Subir el fichero de credenciales de Google
# (desde tu máquina local)
scp credentials.json usuario@tu-ip-hetzner:/ruta/agente-cualificacion-leads/
```

### Crear servicio systemd (arranca automáticamente)

```bash
sudo nano /etc/systemd/system/lead-bot.service
```

Contenido del fichero:

```ini
[Unit]
Description=Orbyn Lead Qualification Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/agente-cualificacion-leads
EnvironmentFile=/home/ubuntu/agente-cualificacion-leads/.env
ExecStart=/home/ubuntu/agente-cualificacion-leads/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# Activar y arrancar el servicio
sudo systemctl daemon-reload
sudo systemctl enable lead-bot
sudo systemctl start lead-bot

# Verificar que está corriendo
sudo systemctl status lead-bot

# Ver logs en tiempo real
sudo journalctl -u lead-bot -f
```

---

## Casos de prueba

| Mensaje | Resultado esperado |
|---|---|
| "Consultoría de RRHH, 15 empleados, Madrid, quieren automatizar el onboarding" | ✅ CUALIFICADO |
| "Agencia de marketing digital, Buenos Aires, 8 personas, buscan IA para campañas" | ✅ CUALIFICADO |
| "Tienda de ropa online, 3 empleados, México" | ❌ NO (tipo + tamaño) |
| "SaaS tech startup, 50 empleados, Nueva York, IA nativa" | ❌ NO (geografía) |
| "Consultoría pequeña en Madrid" | ❌ NO (empleados indeterminados → no cumple mínimo) |

---

## Comandos del bot

| Comando | Descripción |
|---|---|
| `/start` | Mensaje de bienvenida y criterios ICP |
| `/help` | Instrucciones de uso con ejemplos |
| *(cualquier texto)* | Cualificar el lead |

---

## Seguridad y consideraciones de producción

1. **Manejo de errores:** Reintentos con backoff exponencial en llamadas a Gemini y Sheets. Validación estricta del JSON de respuesta. Handler de excepciones con respuesta de fallback al usuario para que nunca quede sin respuesta.

2. **Prompt injection:** El input del usuario se inyecta entre delimitadores XML (`<lead_data>...</lead_data>`) como dato, nunca como instrucción directa. El system prompt está hardcodeado y es inmutable.

3. **Costes y escalabilidad:** Con Gemini Flash gratuito (~3.000 cualificaciones/día). En producción real: rate limiting por usuario (máx. N leads/hora), caché de respuestas para leads idénticos, alertas de cuota mediante Cloud Monitoring, y migración a Gemini Pro si se necesita mayor precisión.

---

## Estructura del proyecto

```
agente-cualificacion-leads/
├── main.py                  # Punto de entrada
├── config.py                # Variables de entorno
├── bot/
│   ├── handlers.py          # Handlers de Telegram
│   └── messages.py          # Templates de respuesta
├── services/
│   ├── qualifier.py         # Lógica de cualificación (Gemini)
│   └── sheets.py            # Logging en Google Sheets
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
