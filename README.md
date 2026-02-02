# B2B Invoice Payment Prediction Agent

Sistema multiagente para predicción de pagos de facturas B2B, integrando datos de Odoo con modelos de machine learning.

![Python](https://img.shields.io/badge/Python-3.13+-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

---

## Descripción

Este proyecto implementa un asistente financiero inteligente que ayuda a gestionar cobros en entornos B2B. Utiliza una arquitectura multiagente basada en LangGraph para:

- Consultar información de clientes y facturas desde Odoo
- Predecir el riesgo de impago de facturas usando modelos ML
- Analizar tendencias de pago y generar reportes (aging, portfolio)
- Mantener notas y alertas sobre clientes

**Tecnologías principales:**
- LangGraph + Mistral AI (orquestación de agentes)
- FastAPI (API REST)
- A2A Protocol (comunicación entre agentes)
- MCP (Model Context Protocol para servicios ML)
- Streamlit (interfaz de usuario)
- Docker Compose (despliegue)

---

## Arquitectura

El sistema sigue una arquitectura multiagente donde un **Orquestador** coordina la ejecución de agentes especializados. La comunicación entre agentes utiliza el protocolo **A2A (Agent-to-Agent)**, mientras que los servicios de ML y persistencia de datos se exponen mediante **MCP (Model Context Protocol)**.



![Diagrama de Arquitectura](https://i.postimg.cc/KzJK1x4h/Mermaid-Chart-Create-complex-visual-diagrams-with-text-2026-01-29-174321.png)

El frontend Streamlit se comunica con el Orquestador via REST API. Este analiza la consulta del usuario, genera un plan de ejecucion y delega tareas a los sub-agentes segun sea necesario. Los agentes acceden a Odoo para datos, al servicio de prediccion para analisis ML, y al servicio de memoria para notas persistentes.

### Módulos

| Módulo | Descripción |
|--------|-------------|
| `apps/orchestrator/` | Orquestador principal que planifica y coordina sub-agentes |
| `apps/agents/` | Sub-agentes especializados (data, analysis, memory) |
| `apps/frontend/` | Interfaz Streamlit para interacción con usuarios |
| `shared/` | Código compartido: clientes, modelos, utilidades |
| `services/` | Servidores MCP para prediccion y memoria |

---

## Requisitos

- Python 3.13+
- Docker y Docker Compose
- uv (gestor de paquetes Python)
- Credenciales de Odoo (URL, DB, usuario, password)
- API Key de Mistral AI
- (Opcional) API Key de LangSmith para tracing

---

## Instalacion

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/ai-agent-invoice-payment-prediction-b2b.git
cd ai-agent-invoice-payment-prediction-b2b
```

### 2. Configurar variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Odoo
ODOO_URL=https://tu-instancia.odoo.com
ODOO_DB=nombre_base_datos
ODOO_USERNAME=usuario@email.com
ODOO_PASSWORD=tu_password

# Mistral AI
API_MISTRAL_KEY=tu_api_key_mistral

# LangSmith (opcional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=tu_api_key_langsmith
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# PostgreSQL (para Docker)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=agent_memory
```

### 3. Instalar dependencias (desarrollo local)

```bash
uv sync
```

---

## Uso

### 1. Levantar servicios con Docker

```bash
docker-compose up -d
```

Esto levanta:
- PostgreSQL (puerto 5432)
- Memory MCP Server (puerto 8100)
- Prediction MCP Server (puerto 8200)
- Data Agent (puerto 8001)
- Analysis Agent (puerto 8002)
- Memory Agent (puerto 8003)
- Orchestrator (puerto 8004)

### 2. Ejecutar el frontend

```bash
uv run streamlit run apps/frontend/chat.py
```

### 3. Ejemplos de consultas

- "Dame informacion sobre el cliente Acme Corp"
- "Cuales son las facturas vencidas de Elogia?"
- "Predice el riesgo de la factura INV-2024-001"
- "Genera un aging report global"
- "Compara los clientes con ID 10 y 15"
- "Recuerda que Acme tiene problemas de tesoreria"

---

## Estructura del Proyecto

```
ai-agent-invoice-payment-prediction-b2b/
├── apps/
│   ├── agents/                 # Sub-agentes
│   │   ├── data_agent/         # Consulta datos de Odoo
│   │   ├── analysis_agent/     # Análisis y predicciones
│   │   └── memory_agent/       # Gestión de notas/alertas
│   ├── orchestrator/           # Orquestador principal
│   │   ├── graph.py            # Grafo LangGraph
│   │   ├── prompts.py          # Prompts del router
│   │   └── main.py             # Servidor FastAPI
│   └── frontend/
│       └── chat.py             # Interfaz Streamlit
├── shared/
│   ├── clients/                # Clientes A2A y MCP
│   ├── config/                 # Configuración (Pydantic Settings)
│   ├── data/                   # DataManager, Cleaner, Retriever
│   ├── models/                 # Modelos de dominio (Pydantic)
│   └── utils/                  # Utilidades (chart_generator)
├── services/
│   ├── prediction_mcp/         # Servidor MCP de predicción
│   └── memory_mcp/             # Servidor MCP de memoria
├── docker/
│   ├── agents/                 # Dockerfile para agentes
│   ├── prediction_mcp/         # Dockerfile para predicción MCP
│   └── memory_mcp/             # Dockerfile para memoria MCP
├── models/
│   └── late_invoice_payment_classification.pkl
├── docs/                       # Documentación Sphinx
├── notebooks/                  # Notebooks de exploracion
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Configuración

### Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `ODOO_URL` | URL de la instancia Odoo | Si |
| `ODOO_DB` | Nombre de la base de datos | Si |
| `ODOO_USERNAME` | Usuario de Odoo | Si |
| `ODOO_PASSWORD` | Password de Odoo | Si |
| `API_MISTRAL_KEY` | API Key de Mistral AI | Si |
| `LANGCHAIN_TRACING_V2` | Activar tracing LangSmith | No |
| `LANGCHAIN_API_KEY` | API Key de LangSmith | No |
| `POSTGRES_USER` | Usuario PostgreSQL | Si (Docker) |
| `POSTGRES_PASSWORD` | Password PostgreSQL | Si (Docker) |
| `POSTGRES_DB` | Base de datos PostgreSQL | Si (Docker) |

### URLs de Servicios (Docker)

Los servicios se comunican internamente usando nombres de contenedor:

| Servicio | URL Interna | Puerto Externo |
|----------|-------------|----------------|
| Orchestrator | http://orchestrator:8004 | 8004 |
| Data Agent | http://data-agent:8001 | 8001 |
| Analysis Agent | http://analysis-agent:8002 | 8002 |
| Memory Agent | http://memory-agent:8003 | 8003 |
| Prediction MCP | http://prediction-mcp:8200 | 8200 |
| Memory MCP | http://memory-mcp:8100 | 8100 |
| PostgreSQL | postgres:5432 | 5432 |

---

## Documentación

### Generar documentacion con Sphinx

```bash
cd docs

# Generar archivos .rst desde el código
uv run sphinx-apidoc -f -o . ../apps -e --implicit-namespaces
uv run sphinx-apidoc -f -o . ../shared -e --implicit-namespaces
uv run sphinx-apidoc -f -o . ../services -e --implicit-namespaces

# Construir HTML
uv run ./make.bat html   # Windows
uv run make html         # Linux/Mac

# Abrir documentación
start _build/html/index.html   # Windows
open _build/html/index.html    # Mac
```

---

## Desarrollo

### Añadir un nuevo agente

1. Crear carpeta en `apps/agents/nuevo_agent/`
2. Implementar:
   - `prompts.py` - Prompt del sistema
   - `tools.py` - Herramientas disponibles
   - `graph.py` - Clase del agente (heredar de `BaseAgent`)
   - `service.py` - Servicio A2A
3. Registrar en `docker-compose.yml`
4. Añadir cliente en `apps/orchestrator/graph.py`

### Logs de Docker

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f orchestrator
```

---

## Licencia

Este proyecto es parte de un Trabajo de Fin de Grado (TFG) de la Escuela de Ingeniería de la Universidad Autónoma de Barcelona.

## Autor

Ismael Fernandez Zarza - 2025
