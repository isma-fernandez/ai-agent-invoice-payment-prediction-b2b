# start_a2a_services.bat
@echo off
echo Activando entorno virtual y iniciando servicios A2A...

call .venv\Scripts\activate.bat

echo Iniciando Data Agent A2A en puerto 8001...
start "Data Agent A2A" cmd /k ".venv\Scripts\activate.bat && python -m src.a2a.services.data_agent_service"
timeout /t 2 /nobreak >nul

echo Iniciando Analysis Agent A2A en puerto 8002...
start "Analysis Agent A2A" cmd /k ".venv\Scripts\activate.bat && python -m src.a2a.services.analysis_agent_service"
timeout /t 2 /nobreak >nul

echo Iniciando Memory Agent A2A en puerto 8003...
start "Memory Agent A2A" cmd /k ".venv\Scripts\activate.bat && python -m src.a2a.services.memory_agent_service"
timeout /t 2 /nobreak >nul

echo.
echo Servicios A2A iniciados en ventanas separadas
echo    - Data Agent: http://localhost:8001
echo    - Analysis Agent: http://localhost:8002
echo    - Memory Agent: http://localhost:8003
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause