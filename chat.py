import streamlit as st
import time
from src.agent.agent import FinancialAgent


st.title("Asistente de facturación")

# Inicializar el agente financiero y el estado del chat
if "agent" not in st.session_state:
    with st.spinner("Iniciando el agente financiero..."):
        st.session_state.agent = FinancialAgent()
        st.success("Agente conectado correctamente.")
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": """
                ¡Hola! Soy tu asistente financiero. Puedo ayudarte con las siguientes tareas

1. **Buscar información sobre clientes:** Obtener detalles de un cliente por su nombre.
2. **Consultar estadísticas de pago:** Ver historial y métricas clave.
3. **Ver facturas:** Revisar facturas pagadas, pendientes o vencidas.
4. **Predecir riesgo de impago:** Evaluar facturas existentes o hipotéticas.

¿Qué te gustaría hacer hoy?
            """.strip()  # .strip() elimina el primer y último salto de línea vacíos
        }
    ]
# Mostrar el historial del chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

    


if prompt := st.chat_input("Escribe tu consulta sobre facturación..."):
    # Agregar el mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Mostrar el mensaje del usuario en la interfaz
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar la entrada del usuario y obtener la respuesta del agente
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            full_response_state = st.session_state.agent.process_request(prompt)
            
            # Extraer el contenido del mensaje de la respuesta del agente
            if "messages" in full_response_state and full_response_state["messages"]:
                agent_response_content = full_response_state["messages"][-1].content
            else:
                agent_response_content = "El agente no devolvió ningún mensaje."

            # TODO: No es ideal, langchain debería soportar streaming nativamente
            display_text = ""
            for char in agent_response_content:
                display_text += char
                message_placeholder.markdown(display_text + "▌")
                time.sleep(0.005) 
            
            message_placeholder.markdown(agent_response_content)
            st.session_state.messages.append({"role": "assistant", "content": agent_response_content})

        except Exception as e:
            st.error(f"Ocurrió un error al procesar tu solicitud: {e}")