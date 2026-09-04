@echo off
echo Starting Custos Autonomous Merchant Finance Agent...
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. 
    echo Please run the following in your terminal first:
    echo 1. python -m venv .venv
    echo 2. .\.venv\Scripts\activate
    echo 3. pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/2] Running the autonomous pipeline to process events...
call .\.venv\Scripts\python.exe run_pipeline.py
if %errorlevel% neq 0 (
    echo [ERROR] Pipeline failed.
    pause
    exit /b %errorlevel%
)
echo.

echo [2/2] Starting the web dashboard...
echo The dashboard will be available at: http://127.0.0.1:8000
echo Press CTRL+C to stop the server.
echo.
call .\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
pause
