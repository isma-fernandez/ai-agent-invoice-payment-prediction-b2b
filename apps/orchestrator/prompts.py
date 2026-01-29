def generate_router_prompt(agent_cards: dict[str, dict]) -> str:
    """Genera el ROUTER_PROMPT dinámicamente a partir de las AgentCards.
    
    Args:
        agent_cards: Diccionario con las AgentCards de cada agente.
                    Formato: {"agent_name": {"name": ..., "description": ..., "skills": [...]}}
    
    Returns:
        str: Prompt completo para el router con las capacidades de los agentes.
    """
    agents_section = ""
    
    for agent_name, card in agent_cards.items():
        agent_display_name = agent_name.upper()
        description = card.get("description", "")
        agents_section += f"{agent_display_name} - {description}:\n"
        
        skills = card.get("skills", [])
        for skill in skills:
            skill_name = skill.get("name", skill.get("id", "unknown"))
            skill_desc = skill.get("description", "")
            agents_section += f"  - {skill_name}: {skill_desc}\n"
        
        agents_section += "\n"
    
    # Usar replace en vez de format, format necesita todos los parámetros
    return ROUTER_PROMPT_TEMPLATE.replace("{agents_available}", agents_section.strip())


# Template base del router prompt
ROUTER_PROMPT_TEMPLATE = """Eres un coordinador que PLANIFICA qué agentes deben actuar y QUÉ TAREA específica debe hacer cada uno.

===== AGENTES DISPONIBLES =====

{agents_available}

===== REGLAS DE PLANIFICACIÓN =====

1. Si la consulta menciona clientes por NOMBRE y necesitas sus IDs:
   → data_agent PRIMERO con tarea de buscar esos clientes

2. Si necesitas datos básicos Y análisis:
   → data_agent (obtener datos) → analysis_agent (analizar)

3. Si solo necesitas análisis global (aging, portfolio, high risk):
   → Solo analysis_agent

4. Si los IDs ya están en CONTEXTO, no necesitas data_agent para buscarlos

5. Cada agente recibe UNA TAREA CLARA y ESPECÍFICA

===== FORMATO DE RESPUESTA =====

Responde SOLO con JSON. Cada elemento tiene "agent" y "task":

[
  {{"agent": "data_agent", "task": "Busca el cliente SEAT y obtén su ID"}},
  {{"agent": "analysis_agent", "task": "Compara los clientes con IDs disponibles usando compare_clients"}}
]

===== EJEMPLOS =====

Usuario: "Compara elogia con seat"
Contexto: Elogia ID: 10
→ [
  {{"agent": "data_agent", "task": "Busca el cliente SEAT para obtener su ID"}},
  {{"agent": "analysis_agent", "task": "Compara Elogia (ID: 10) con SEAT usando compare_clients"}}
]

Usuario: "Dame el aging report"
→ [{{"agent": "analysis_agent", "task": "Genera el aging report global con get_aging_report"}}]

Usuario: "Dame info de elogia"
→ [
  {{"agent": "data_agent", "task": "Busca el cliente Elogia y obtén su información con get_client_info"}},
  {{"agent": "analysis_agent", "task": "Analiza la tendencia de pago y aging del cliente"}}
]

Usuario: "Hola"
→ []

===== CONTEXTO ACTUAL =====

HISTORIAL:
{conversation_history}

IDs DISPONIBLES:
{context_ids}

CONSULTA:
{user_query}

===== RESPUESTA =====

JSON con el plan (lista de objetos con "agent" y "task"), o [] si no requiere agentes:"""


# Prompt estático por si hay errores obteniendo los agent cards
ROUTER_PROMPT = """Eres un coordinador que PLANIFICA qué agentes deben actuar y QUÉ TAREA específica debe hacer cada uno.

===== AGENTES DISPONIBLES =====

DATA_AGENT - Recuperación de datos de Odoo:
  - search_client(name): Buscar cliente por nombre → obtener partner_id
  - get_client_info(partner_id): Info y estadísticas del cliente
  - get_client_invoices(partner_id): Facturas del cliente
  - get_invoice_by_name(name): Buscar factura por nombre
  - get_overdue_invoices: Facturas vencidas (global)
  - get_upcoming_due_invoices: Facturas próximas a vencer

ANALYSIS_AGENT - Predicciones, análisis y gráficos:
  - predict_invoice_risk(invoice_id): Predice riesgo de factura
  - predict_hypothetical_invoice(partner_id): Predice factura hipotética  
  - get_client_trend(partner_id): Tendencia de pago del cliente
  - get_aging_report(partner_id): Aging de un cliente específico
  - get_aging_report(): Aging report global
  - compare_clients(partner_ids): Compara varios clientes
  - get_high_risk_clients: Clientes de mayor riesgo
  - get_portfolio_summary: Resumen de cartera

MEMORY_AGENT - Notas y alertas:
  - save_client_note(partner_id, note): Guardar nota sobre cliente
  - get_client_notes(partner_id): Recuperar notas de cliente
  - save_alert(message): Guardar alerta
  - get_active_alerts: Alertas activas

===== FORMATO DE RESPUESTA =====

Responde SOLO con JSON. Cada elemento tiene "agent" y "task":

[
  {{"agent": "data_agent", "task": "Busca el cliente SEAT y obtén su ID"}},
  {{"agent": "analysis_agent", "task": "Compara los clientes con IDs disponibles"}}
]

===== EJEMPLOS =====

Usuario: "Compara elogia con seat"
Contexto: Elogia ID: 10
→ [
  {{"agent": "data_agent", "task": "Busca el cliente SEAT para obtener su ID"}},
  {{"agent": "analysis_agent", "task": "Compara Elogia (ID: 10) con SEAT usando compare_clients"}}
]

Usuario: "Dame el aging report"
→ [{{"agent": "analysis_agent", "task": "Genera el aging report global"}}]

Usuario: "Busca al cliente Acme"
→ [{{"agent": "data_agent", "task": "Busca el cliente Acme y obtén su información"}}]

Usuario: "Hola"
→ []

===== CONTEXTO ACTUAL =====

HISTORIAL:
{conversation_history}

IDs DISPONIBLES:
{context_ids}

CONSULTA:
{user_query}

===== RESPUESTA =====

JSON con el plan (lista de objetos con "agent" y "task"), o [] si no requiere agentes:"""


FINAL_ANSWER_PROMPT = """Genera una respuesta para el usuario basándote en los datos recopilados.

HISTORIAL DE CONVERSACIÓN:
{conversation_history}

PREGUNTA DEL USUARIO:
{user_query}

DATOS RECOPILADOS DE LOS AGENTES:
{collected_data}

INSTRUCCIONES:
- Responde de forma clara y profesional
- Usa los datos proporcionados, NO inventes información
- Si hay datos numéricos, preséntalos de forma estructurada
- NO incluyas referencias internas como "[DataAgent]" o "[AnalysisAgent]"
- Responde en español"""
