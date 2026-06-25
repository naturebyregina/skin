@echo off
echo Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Download from https://www.python.org/
    pause
    exit /b 1
)

echo Creating virtual environment...
if not exist "venv" python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Opening browser...
timeout /t 2
start http://localhost:5000

echo Starting app...
python app.py
pause