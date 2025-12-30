from langchain_core.tools import tool
from src.data.manager import DataManager
from src.data.models import *
from src.agent.memory.store import MemoryStore
from src.agent.memory.models import Memory, MemoryType

data_manager: DataManager = None
memory_store: MemoryStore = None


async def initialize_data_manager(model_path: str = None):
    """Inicializa el DataManager. Llamar antes de usar las tools."""
    global data_manager, memory_store
    data_manager = DataManager(cutoff_date="2025-01-01")
    await data_manager.connect()
    #TODO: reactivar
    #if model_path:
        #data_manager.load_model(model_path)
    memory_store = MemoryStore()



#
# ======================= MEMORY TOOLS ===============================
#

"""
tools = [
    search_client,
    get_client_info,
    get_client_invoices,
    get_invoice_by_name, # no funciona :/
    predict_invoice_risk,
    predict_hypothetical_invoice,
    check_connection,
    get_overdue_invoices,
    get_high_risk_clients, # te dice que devuelve 10 pero devuelve 4, lento de cojones tmb
    compare_clients, # ok, falla a veces
    get_upcoming_due_invoices, # funciona más o menos (coge las facturas de empresas descartadas)
    get_aging_report, # no tiene en cuenta las facturas que no estan en euros
    get_portfolio_summary, # extra lento de cojones, el sintetizador lo resume demasiado por alguna razón

    ⚠️ Alerta
Solo 1 factura no vencida (18 €): Riesgo de que toda la cartera pase a vencido si no se actúa.
Próximos pasos sugeridos:

Analizar las 10 facturas más grandes vencidas.
Revisar tendencias de pago de clientes clave (ej: Elogia Media S.L. vs. Kraz Data Solutions SL).????

    get_client_trend, # No funciona, se inventa el partner id ns pq

    Dame la tendencia del cliente elogia

get_client_trend

Ocurrió un error: La factura con ID 12345 no existe.

Traceback (most recent call last):
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\chat.py", line 106, in <module>
    final_response = asyncio.run(run_stream(
        st.session_state.agent,
    ...<3 lines>...
        message_placeholder
    ))
  File "C:\Users\Ismae\AppData\Roaming\uv\python\cpython-3.13.11-windows-x86_64-none\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "C:\Users\Ismae\AppData\Roaming\uv\python\cpython-3.13.11-windows-x86_64-none\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Users\Ismae\AppData\Roaming\uv\python\cpython-3.13.11-windows-x86_64-none\Lib\asyncio\base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\chat.py", line 51, in run_stream
    async for event in agent.stream_request(prompt, thread_id):
    ...<39 lines>...
                    last_complete_response = response_text
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\src\agents\orchestrator\agent.py", line 44, in stream_request
    async for event in self._orchestrator.stream(request, thread_id):
        yield event
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\src\agents\orchestrator\graph.py", line 315, in stream
    async for event in self.graph.astream_events(initial_state, config=config):
        yield event
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\runnables\base.py", line 1514, in astream_events
    async for event in event_stream:
        yield event
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tracers\event_stream.py", line 1082, in _astream_events_implementation_v2
    await task
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tracers\event_stream.py", line 1037, in consume_astream
    async for _ in event_streamer.tap_output_aiter(run_id, stream):
        # All the content will be picked up
        pass
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tracers\event_stream.py", line 215, in tap_output_aiter
    async for chunk in output:
    ...<4 lines>...
        yield chunk
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\pregel\main.py", line 2971, in astream
    async for _ in runner.atick(
    ...<13 lines>...
            yield o
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\pregel\_runner.py", line 304, in atick
    await arun_with_retry(
    ...<15 lines>...
    )
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\pregel\_retry.py", line 132, in arun_with_retry
    async for _ in task.proc.astream(task.input, config):
        pass
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 839, in astream
    output = await asyncio.create_task(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
        _consume_aiter(aiterator), context=context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 904, in _consume_aiter
    async for chunk in it:
    ...<8 lines>...
            output = chunk
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tracers\event_stream.py", line 192, in tap_output_aiter
    first = await anext(output, sentinel)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\runnables\base.py", line 1587, in atransform
    async for ichunk in input:
    ...<14 lines>...
                final = ichunk
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\runnables\base.py", line 1168, in astream
    yield await self.ainvoke(input, config, **kwargs)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 473, in ainvoke
    ret = await self.afunc(*args, **kwargs)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\src\agents\orchestrator\graph.py", line 204, in _run_analysis_agent
    result = await self.analysis_agent.run([HumanMessage(content=context)])
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\src\agents\base_agent.py", line 97, in run
    return await self.graph.ainvoke({"messages": messages})
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\pregel\main.py", line 3158, in ainvoke
    async for chunk in self.astream(
    ...<29 lines>...
            chunks.append(chunk)
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\pregel\main.py", line 2971, in astream
    async for _ in runner.atick(
    ...<13 lines>...
            yield o
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\pregel\_runner.py", line 304, in atick
    await arun_with_retry(
    ...<15 lines>...
    )
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\pregel\_retry.py", line 132, in arun_with_retry
    async for _ in task.proc.astream(task.input, config):
        pass
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 839, in astream
    output = await asyncio.create_task(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
        _consume_aiter(aiterator), context=context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 904, in _consume_aiter
    async for chunk in it:
    ...<8 lines>...
            output = chunk
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tracers\event_stream.py", line 192, in tap_output_aiter
    first = await anext(output, sentinel)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\runnables\base.py", line 1587, in atransform
    async for ichunk in input:
    ...<14 lines>...
                final = ichunk
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\runnables\base.py", line 1168, in astream
    yield await self.ainvoke(input, config, **kwargs)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 473, in ainvoke
    ret = await self.afunc(*args, **kwargs)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\src\agents\base_agent.py", line 86, in _run_tools
    return await self.tool_node.ainvoke(state)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 473, in ainvoke
    ret = await self.afunc(*args, **kwargs)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 832, in _afunc
    outputs = await asyncio.gather(*coros)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 1163, in _arun_one
    return await self._execute_tool_async(tool_request, input_type, config)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 1112, in _execute_tool_async
    content = _handle_tool_error(e, flag=self._handle_tool_errors)
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 424, in _handle_tool_error
    content = flag(e)  # type: ignore [assignment, call-arg]
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 381, in _default_handle_tool_errors
    raise e
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 1069, in _execute_tool_async
    response = await tool.ainvoke(call_args, config)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tools\structured.py", line 66, in ainvoke
    return await super().ainvoke(input, config, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tools\base.py", line 639, in ainvoke
    return await self.arun(tool_input, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tools\base.py", line 1111, in arun
    raise error_to_raise
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tools\base.py", line 1077, in arun
    response = await coro_with_context(coro, context)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\.venv\Lib\site-packages\langchain_core\tools\structured.py", line 120, in _arun
    return await self.coroutine(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\src\agents\analysis_agent\tools.py", line 21, in predict_invoice_risk
    return await dm.predict(invoice_id=invoice_id)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ismae\Documents\TFG\ai-agent-invoice-payment-prediction-b2b\src\data\manager.py", line 191, in predict
    raise ValueError(f"La factura con ID {invoice_id} no existe.")
ValueError: La factura con ID 12345 no existe.
During task with name 'tools' and id '119308b5-ff26-ebfa-ac4a-d2dcd73672b8'
During task with name 'analysis_agent' and id 'a1bc5417-e124-9f49-e41f-ac475053839f'
    get_deteriorating_clients, # LENTISIMO de cojones, y tampoco lo hace demasiado bien la verdad, devuelve 2 tristes clientes
    get_invoices_by_period,
    save_client_note,
    get_client_notes,
    save_alert,
    get_active_alerts,
]
"""