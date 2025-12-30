import asyncio
import re
import uuid
import streamlit as st
from src.agents.orchestrator import FinancialAgent
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
            "content": """¡Hola! Soy tu asistente financiero. Puedo ayudarte con las siguientes tareas
        
1. **Buscar información sobre clientes:** Obtener detalles de un cliente por su nombre.
2. **Consultar estadísticas de pago:** Ver historial y métricas clave.
3. **Ver facturas:** Revisar facturas pagadas, pendientes o vencidas.
4. **Predecir riesgo de impago:** Evaluar facturas existentes o hipotéticas.

¿Qué te gustaría hacer hoy?"""
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


async def run_stream(agent, prompt, thread_id, status_placeholder, message_placeholder):
    """Ejecuta el agente en modo streaming."""
    response_text = ""
    current_tool = None
    last_complete_response = ""

    async for event in agent.stream_request(prompt, thread_id):
        kind = event.get("event")
        name = event.get("name", "")

        # Ignorar eventos del router (para evitar msgs de "data_analyst", ...)
        if "router" in name.lower():
            continue

        if kind == "on_tool_start":
            tool_name = event.get("name", "herramienta")
            current_tool = tool_name
            status_placeholder.info(f"Usando: {tool_name}...")

        elif kind == "on_tool_end":
            if current_tool:
                status_placeholder.success(f"{current_tool}")
            current_tool = None

        elif kind == "on_chat_model_start":
            response_text = ""
            status_placeholder.info("Procesando...")

        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                response_text += chunk.content
                message_placeholder.markdown(response_text + "|")

        elif kind == "on_chat_model_end":
            status_placeholder.empty()
            output = event.get("data", {}).get("output")

            if output and hasattr(output, "tool_calls") and output.tool_calls:
                response_text = ""
                message_placeholder.empty()
            elif response_text:
                last_complete_response = response_text

    return last_complete_response if last_complete_response else response_text


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
                # Eliminar gráficos del texto
                chart_matches = re.findall(r'CHART:([a-f0-9]+)', final_response)
                clean_response = re.sub(r'CHART:[a-f0-9]+', '', final_response).strip()
                message_placeholder.markdown(clean_response)

                # Renderizar gráficos
                for chart_id in chart_matches:
                    fig = chart_generator.get_chart(chart_id)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                        chart_generator.clear_chart(chart_id)

                st.session_state.messages.append({"role": "assistant", "content": clean_response})
            else:
                final_response = asyncio.run(st.session_state.agent.process_request(
                    prompt, thread_id=st.session_state.thread_id
                ))
                message_placeholder.markdown(final_response)
                st.session_state.messages.append({"role": "assistant", "content": final_response})

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
            import traceback

            st.code(traceback.format_exc())
