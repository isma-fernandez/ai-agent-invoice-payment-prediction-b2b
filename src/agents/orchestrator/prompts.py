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
    
    return ROUTER_PROMPT_TEMPLATE.format(agents_available=agents_section.strip())


# Template base del router prompt
ROUTER_PROMPT_TEMPLATE = """Eres un coordinador que PLANIFICA qué agentes deben actuar para responder la consulta.

Tu trabajo es analizar la consulta y devolver UNA LISTA de agentes necesarios, en orden de ejecución.

===== AGENTES DISPONIBLES =====

{agents_available}

===== REGLAS DE PLANIFICACIÓN =====

1. Si la consulta menciona clientes por NOMBRE y necesitas sus IDs:
   → Incluir data_agent PRIMERO para buscar IDs

2. Si necesitas datos básicos (facturas, info cliente) Y análisis:
   → [data_agent, analysis_agent]

3. Si solo necesitas análisis global (aging, portfolio, high risk):
   → [analysis_agent]

4. Si la consulta hace referencia contextual ("sus", "ese cliente") y los IDs están en el HISTORIAL:
   → Usar esos IDs directamente, no necesitas data_agent

5. Si es un saludo o pregunta general sin necesidad de Odoo:
   → []

===== EJEMPLOS =====

"Compara elogia con seat"
→ [data_agent, analysis_agent]
(Primero buscar IDs, luego comparar)

"Dame el aging report"
→ [analysis_agent]
(No necesita IDs, es global)

"Dame sus aging buckets" (con IDs en historial)
→ [analysis_agent]
(Ya tiene los IDs del contexto)

"Busca al cliente Acme"
→ [data_agent]
(Solo búsqueda)

"Predice el riesgo de la factura INV-001"
→ [data_agent, analysis_agent]
(Buscar factura, luego predecir)

"Hola, qué puedes hacer?"
→ []
(No requiere agentes)

===== CONTEXTO =====

HISTORIAL:
{conversation_history}

IDs DISPONIBLES EN CONTEXTO:
{context_ids}

CONSULTA DEL USUARIO:
{user_query}

===== RESPUESTA =====

Responde SOLO con la lista de agentes en formato JSON:
["data_agent", "analysis_agent"]
o
["analysis_agent"]
o
[]

NO incluyas explicaciones, SOLO el JSON."""


# Prompt estático por si hay errores obteniendo los agent cards
ROUTER_PROMPT = """Eres un coordinador que PLANIFICA qué agentes deben actuar para responder la consulta.

Tu trabajo es analizar la consulta y devolver UNA LISTA de agentes necesarios, en orden de ejecución.

===== AGENTES DISPONIBLES =====

DATA_AGENT - Recuperación de datos de Odoo:
  - search_client(name): Buscar cliente por nombre → obtener partner_id
  - get_client_info(partner_id): Info y estadísticas del cliente
  - get_client_invoices(partner_id): Facturas del cliente
  - get_invoice_by_name(name): Buscar factura por nombre
  - get_overdue_invoices: Facturas vencidas (NO necesita IDs)
  - get_upcoming_due_invoices: Facturas próximas a vencer
  - check_connection: Verificar conexión

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
  - save_client_note: Guardar nota sobre cliente. REQUIERE partner_id.
  - get_client_notes: Recuperar notas de cliente. REQUIERE partner_id.
  - save_alert: Guardar alerta. partner_id OPCIONAL.
  - get_active_alerts: Alertas activas. NO requiere IDs, es global.

===== REGLAS DE PLANIFICACIÓN =====

1. Si la consulta menciona clientes por NOMBRE y necesitas sus IDs:
   → Incluir data_agent PRIMERO para buscar IDs

2. Si necesitas datos básicos (facturas, info cliente) Y análisis:
   → [data_agent, analysis_agent]

3. Si solo necesitas análisis global (aging, portfolio, high risk):
   → [analysis_agent]

4. Si la consulta hace referencia contextual ("sus", "ese cliente") y los IDs están en el HISTORIAL:
   → Usar esos IDs directamente, no necesitas data_agent

5. Si es un saludo o pregunta general sin necesidad de Odoo:
   → []

===== EJEMPLOS =====

"Compara elogia con seat"
→ [data_agent, analysis_agent]
(Primero buscar IDs, luego comparar)

"Dame el aging report"
→ [analysis_agent]
(No necesita IDs, es global)

"Dame sus aging buckets" (con IDs en historial)
→ [analysis_agent]
(Ya tiene los IDs del contexto)

"Busca al cliente Acme"
→ [data_agent]
(Solo búsqueda)

"Predice el riesgo de la factura INV-001"
→ [data_agent, analysis_agent]
(Buscar factura, luego predecir)

"Hola, qué puedes hacer?"
→ []
(No requiere agentes)

===== CONTEXTO =====

HISTORIAL:
{conversation_history}

IDs DISPONIBLES EN CONTEXTO:
{context_ids}

CONSULTA DEL USUARIO:
{user_query}

===== RESPUESTA =====

Responde SOLO con la lista de agentes en formato JSON:
["data_agent", "analysis_agent"]
o
["analysis_agent"]
o
[]

NO incluyas explicaciones, SOLO el JSON."""


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
