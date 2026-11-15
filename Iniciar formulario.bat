@echo off
rem Enciende el formulario en tu computador y abre la pagina de prueba.
rem Para apagarlo, cierra la ventana negra.
cd /d "%~dp0"
start "Formulario Rebajitas COD (no cerrar)" cmd /k ".venv\Scripts\python.exe app.py"
timeout /t 4 /nobreak >nul
start "" http://127.0.0.1:8001/prueba
