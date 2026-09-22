@echo off
rem ============================================================
rem  ApoloVibes - Levanta DB + Backend interno + API Gateway
rem  (No levanta el frontend: eso se hace con npm run dev)
rem ============================================================
setlocal
cd /d "%~dp0"

echo.
echo  [1/4] Validando entorno...

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  ERROR: No existe .venv\. Crealo antes:
    echo    python -m venv .venv
    echo    .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

where docker >nul 2>&1
if errorlevel 1 (
    echo  AVISO: 'docker' no esta en el PATH. La DB de Postgres no se levantara.
    echo          (Solo funciona si .env apunta a Oracle con ORACLE_DSN.)
) else (
    echo.
    echo  [2/4] Levantando PostgreSQL...
    docker compose up -d db
)

echo.
echo  [3/4] Abriendo Backend interno  (puerto 8000, no usar directo)...
start "ApoloVibes | Backend :8000" cmd /k ""%~dp0.venv\Scripts\python.exe" -m flask --app app run --port 8000"

echo  [4/4] Abriendo API Gateway publico  (puerto 3000)...
start "ApoloVibes | Gateway :3000" cmd /k ""%~dp0.venv\Scripts\python.exe" -m flask --app gateway.main run --port 3000"

echo.
echo  Resumen:
echo    - Backend : http://localhost:8000      (interno, confia en el gateway)
echo    - Gateway : http://localhost:3000/api  (publico)
echo    - Frontend: cd ApoloVibes-frontend ; npm run dev
echo.
echo  Cada servicio corre en su propia ventana. Para apagar: Ctrl+C en cada una.
echo.
pause
endlocal