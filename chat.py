import re
import json
import uuid
import httpx
import streamlit as st
import plotly.io as pio

ORCHESTRATOR_URL = "http://localhost:8004"

st.title("Asistente de facturación")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

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


def send_message(prompt: str, thread_id: str) -> str:
    """Envía un mensaje al orchestrator y devuelve la respuesta."""
    with httpx.Client(timeout=900.0) as client:  # 15 minutos
        response = client.post(
            f"{ORCHESTRATOR_URL}/chat",
            json={"message": prompt, "thread_id": thread_id}
        )
        response.raise_for_status()
        return response.json()["response"]


if prompt := st.chat_input("Escribe tu consulta sobre facturación..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        message_placeholder = st.empty()

        try:
            status_placeholder.info("Procesando consulta...")
            
            final_response = send_message(prompt, st.session_state.thread_id)
            
            status_placeholder.empty()

            if final_response:
                clean_response = final_response.replace("CHART:CHART_JSON:", "CHART_JSON:")
                # Extraer gráficos JSON de la respuesta
                charts = []
                while "CHART_JSON:" in clean_response:
                    idx = clean_response.find("CHART_JSON:")
                    json_start = idx + len("CHART_JSON:")
                    try:
                        chart_data, end = json.JSONDecoder().raw_decode(clean_response[json_start:])
                        charts.append(chart_data)
                        clean_response = clean_response[:idx] + clean_response[json_start + end:]
                    except json.JSONDecodeError:
                        break
                
                clean_response = clean_response.strip()
                message_placeholder.markdown(clean_response)

                for chart_data in charts:
                    try:
                        fig = pio.from_json(json.dumps(chart_data))
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Error al renderizar gráfico: {e}")

                st.session_state.messages.append({"role": "assistant", "content": clean_response})
            else:
                message_placeholder.markdown("No se recibió respuesta del servidor.")

        except httpx.ConnectError:
            status_placeholder.empty()
            st.error("No se puede conectar con el orchestrator. ¿Está corriendo Docker?")
        except httpx.HTTPStatusError as e:
            status_placeholder.empty()
            st.error(f"Error del servidor: {e.response.status_code}")
        except Exception as e:
            status_placeholder.empty()
            st.error(f"Error al procesar la consulta: {e}")
            import traceback
            st.code(traceback.format_exc())
