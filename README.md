# 🤖 Agente de Cualificación de Leads — Orbyn

Bot de Telegram que cualifica leads B2B en tiempo real usando IA (Groq) y registra cada evaluación en Google Sheets.

## ¿Qué hace?

1. **Recibe** datos de un lead en texto libre por Telegram
2. **Analiza** con un LLM (Groq) si encaja con el ICP de Orbyn
3. **Responde** en el mismo chat con la decisión, el razonamiento y los criterios evaluados
4. **Loguea** cada lead en Google Sheets con fecha, datos, decisión y criterios
5. **Reintenta** automáticamente si Groq falla por error transitorio (timeout, rate limit)
6. **Detecta** cuando los datos son insuficientes y pide la información que falta en vez de rechazar directamente

### ICP (Ideal Customer Profile) de Orbyn

| Criterio | Requisito |
|---|---|
| Tipo de empresa | Servicios o consultoría |
| Tamaño | Mínimo 5 empleados |
| Geografía | España o Latinoamérica |
| Interés | Automatización o IA |

---

## Stack técnico

| Componente | Herramienta |
|---|---|
| Bot | python-telegram-bot 21.x |
| LLM | Groq (llama-3.3-70b-versatile) |
| Sheets | gspread + Google Sheets API |
| Hosting | Hetzner VPS (systemd) |

---

## Setup

### 1. Crear el bot de Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía `/newbot` y sigue las instrucciones
3. Copia el **token** que te da BotFather

### 2. Obtener API Key de Groq (gratuito)

1. Ve a [console.groq.com](https://console.groq.com)
2. Crea una API Key
3. Copia la key generada

### 3. Configurar Google Sheets

#### 3a. Crear el proyecto en Google Cloud Console
1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuevo proyecto
3. Ve a **APIs & Services → Library**
4. Busca y activa **Google Sheets API**

#### 3b. Crear Service Account
1. Ve a **APIs & Services → Credentials**
2. Haz clic en **"Create Credentials → Service Account"**
3. Dale un nombre (p.ej. `lead-agent-bot`)
4. En la página del service account → **Keys → Add Key → JSON**
5. Descarga el fichero JSON y guárdalo como `credentials.json` en el proyecto

#### 3c. Preparar el Google Sheet
1. Crea un nuevo Google Sheet en [sheets.google.com](https://sheets.google.com)
2. Copia el **ID** de la URL: `docs.google.com/spreadsheets/d/**ESTE_ID**/edit`
3. Haz clic en **Compartir** y añade el email del service account (campo `client_email` del JSON)
4. Dale permiso de **Editor**

### 4. Variables de entorno

Crea un fichero `.env` en la raíz del proyecto:

```env
TELEGRAM_BOT_TOKEN=123456:ABCdef...
GROQ_API_KEY=gsk_...
GOOGLE_CREDENTIALS_FILE=credentials.json
SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
LOG_LEVEL=INFO
```

### 5. Instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 6. Ejecutar localmente

```bash
python main.py
```

---

## Deploy en producción (Hetzner VPS)

```bash
# Conectarte al VPS
ssh root@tu-ip-hetzner

# Clonar el repositorio
cd /home/proyectos
git clone https://github.com/miguelgoyanes/agente-cualificacion-leads.git
cd agente-cualificacion-leads

# Instalar dependencias del sistema si es necesario
apt install python3.12-venv -y

# Entorno virtual
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Crear .env con los valores reales
nano .env

# Subir credentials.json desde tu máquina local
scp credentials.json root@tu-ip-hetzner:/home/proyectos/agente-cualificacion-leads/
```

### Servicio systemd

```bash
# Copiar el fichero de servicio incluido en el repo
cp lead-bot.service /etc/systemd/system/

# Activar y arrancar
systemctl daemon-reload
systemctl enable lead-bot
systemctl start lead-bot

# Verificar
systemctl status lead-bot

# Ver logs en tiempo real
journalctl -u lead-bot -f
```

> El fichero `lead-bot.service` ya incluido en el repo está configurado para arrancar automáticamente con el servidor y reiniciarse si el proceso cae.

---

## Comandos del bot

| Comando | Descripción |
|---|---|
| `/start` | Mensaje de bienvenida y criterios ICP |
| `/help` | Instrucciones de uso con ejemplos |
| *(cualquier texto)* | Cualificar el lead |

---

## Casos de prueba

| Mensaje | Resultado esperado |
|---|---|
| "Consultoría de RRHH, 15 empleados, Madrid, quieren automatizar el onboarding" | ✅ CUALIFICADO |
| "Agencia de marketing digital, Buenos Aires, 8 personas, buscan IA para campañas" | ✅ CUALIFICADO |
| "Tienda de ropa online, 3 empleados, México" | ❌ NO CUALIFICADO (tipo + tamaño) |
| "SaaS tech startup, 50 empleados, Nueva York, IA nativa" | ❌ NO CUALIFICADO (geografía) |
| "Empresa de Madrid" | ❓ DATOS INSUFICIENTES (pide empleados, sector e interés) |

---

## Seguridad y consideraciones de producción

1. **Manejo de errores:** Reintentos automáticos con backoff en llamadas a Groq. Validación estricta del JSON de respuesta. Handler de excepciones con respuesta de fallback para que el usuario nunca quede sin respuesta.

2. **Prompt injection:** El input del usuario se inyecta entre delimitadores XML (`<lead_data>...</lead_data>`) como dato, nunca como instrucción directa. El system prompt está hardcodeado y es inmutable.

3. **Costes y escalabilidad:** Con el tier gratuito de Groq cubre el uso normal. En producción real: rate limiting por usuario, base de datos propia (PostgreSQL) en lugar de Sheets como fuente de verdad, y webhook HTTPS en lugar de polling.

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
│   ├── qualifier.py         # Lógica de cualificación (Groq)
│   └── sheets.py            # Logging en Google Sheets
├── lead-bot.service         # Servicio systemd para producción
├── requirements.txt
├── .gitignore
└── README.md
```
