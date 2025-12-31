import asyncio
import re
import uuid
import streamlit as st
from src.agents.orchestrator import FinancialAgent
from src.agents.messages import get_agent_message, get_tool_message
from src.utils.chart_generator import chart_generator

st.title("Asistente de facturación")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "agent" not in st.session_state:
    with st.spinner("Iniciando el agente financiero..."):
        agent = FinancialAgent()
        asyncio.run(agent.initialize(
            cutoff_date="2025-01-01",
            model_path="models/late_invoice_payment_classification.pkl"
        ))
        st.session_state.agent = agent
        st.success("Agente conectado correctamente.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": """Hola, soy tu asistente financiero. Puedo ayudarte con:

1. **Buscar información sobre clientes:** Obtener detalles de un cliente por su nombre.
2. **Consultar estadísticas de pago:** Ver historial y métricas clave.
3. **Ver facturas:** Revisar facturas pagadas, pendientes o vencidas.
4. **Predecir riesgo de impago:** Evaluar facturas existentes o hipotéticas.
5. **Análisis de cartera:** Aging report, resumen de portfolio, tendencias.

¿Qué te gustaría hacer hoy?"""
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


async def run_stream(agent, prompt, thread_id, status_placeholder, message_placeholder):
    """Ejecuta el agente en modo streaming mostrando solo estados relevantes."""
    final_response = ""
    is_final_answer = False
    current_node = None

    async for event in agent.stream_request(prompt, thread_id):
        kind = event.get("event")
        name = event.get("name", "")

        # Detectar inicio de nodo
        if kind == "on_chain_start":
            node_name = name.lower()

            # Router: ignorar completamente
            if "router" in node_name:
                current_node = "router"
                continue

            # Respuesta final: activar streaming de texto
            if "final_answer" in node_name:
                is_final_answer = True
                current_node = "final_answer"
                status_placeholder.info("Generando respuesta...")
                continue

            # Subagentes: mostrar mensaje correspondiente
            agent_msg = get_agent_message(node_name)
            if agent_msg:
                current_node = node_name
                status_placeholder.info(agent_msg)

        # Herramientas: mostrar mensaje amigable
        elif kind == "on_tool_start":
            tool_name = event.get("name", "")
            tool_msg = get_tool_message(tool_name)
            status_placeholder.info(tool_msg)

        elif kind == "on_tool_end":
            # Restaurar mensaje del agente actual
            if current_node:
                agent_msg = get_agent_message(current_node)
                if agent_msg:
                    status_placeholder.info(agent_msg)

        # Streaming de texto SOLO en respuesta final
        elif kind == "on_chat_model_stream":
            if is_final_answer:
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    final_response += chunk.content
                    message_placeholder.markdown(final_response + "▌")

        elif kind == "on_chat_model_end":
            if is_final_answer:
                status_placeholder.empty()
                if final_response:
                    message_placeholder.markdown(final_response)

        # Fin de nodo
        elif kind == "on_chain_end":
            node_name = name.lower()
            if "final_answer" in node_name:
                is_final_answer = False
            elif current_node and current_node in node_name:
                current_node = None

    return final_response


if prompt := st.chat_input("Escribe tu consulta sobre facturación..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        message_placeholder = st.empty()

        try:
            final_response = asyncio.run(run_stream(
                st.session_state.agent,
                prompt,
                st.session_state.thread_id,
                status_placeholder,
                message_placeholder
            ))

            if final_response:
                # Eliminar marcadores de gráficos del texto
                chart_matches = re.findall(r'CHART:([a-f0-9]+)', final_response)
                clean_response = re.sub(r'CHART:[a-f0-9]+', '', final_response).strip()
                message_placeholder.markdown(clean_response)

                # Renderizar gráficos si existen
                for chart_id in chart_matches:
                    fig = chart_generator.get_chart(chart_id)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                        chart_generator.clear_chart(chart_id)

                st.session_state.messages.append({"role": "assistant", "content": clean_response})
            else:
                # Fallback: proceso sin streaming
                status_placeholder.info("Procesando consulta...")
                final_response = asyncio.run(st.session_state.agent.process_request(
                    prompt, thread_id=st.session_state.thread_id
                ))
                status_placeholder.empty()
                message_placeholder.markdown(final_response)
                st.session_state.messages.append({"role": "assistant", "content": final_response})

        except Exception as e:
            status_placeholder.empty()
            st.error(f"Error al procesar la consulta: {e}")
            import traceback

            st.code(traceback.format_exc())