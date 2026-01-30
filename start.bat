@echo off
setlocal enabledelayedexpansion
title Bhavya Health Data Fetcher
color 0A

:: Prevent window from closing on error
if "%1"=="" (
    cmd /k "%~f0" run
    exit /b
)


:: ============================================================
::  CONFIGURATION SECTION - MODIFY THESE VALUES AS NEEDED
:: ============================================================

:: -------------------------------------------------------
:: PROJECT PATH - Change this to your actual project folder
:: Example: set "PROJECT_DIR=C:\Users\YourName\bhavya_fetcher"
:: Default: %~dp0 (auto-detects current folder where start.bat is located)
:: -------------------------------------------------------
set "PROJECT_DIR=%~dp0"

:: -------------------------------------------------------
:: PYTHON PATH - Change if Python is installed in custom location
:: Example: set "PYTHON_EXE=C:\Python311\python.exe"
:: Example: set "PYTHON_EXE=C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe"
:: Default: "python" (uses system PATH)
:: -------------------------------------------------------
set "PYTHON_EXE=python"

:: -------------------------------------------------------
:: BACKEND APP PATH - Relative path from PROJECT_DIR to app.py
:: Example: set "BACKEND_APP=backend.app:app"
:: Example: set "BACKEND_APP=src.main:app"
:: Default: backend.app:app (looks for PROJECT_DIR\backend\app.py)
:: -------------------------------------------------------
set "BACKEND_APP=backend.app:app"

:: -------------------------------------------------------
:: SERVER CONFIGURATION
:: Change SERVER_HOST to 0.0.0.0 if you want to access from other machines
:: Change SERVER_PORT if 8000 is already in use
:: -------------------------------------------------------
set "SERVER_HOST=127.0.0.1"
set "SERVER_PORT=8000"

:: -------------------------------------------------------
:: FRONTEND PATH - Relative path from PROJECT_DIR to index.html
:: Example: set "FRONTEND_PATH=frontend\index.html"
:: Example: set "FRONTEND_PATH=public\index.html"
:: Default: frontend\index.html
:: -------------------------------------------------------
set "FRONTEND_PATH=frontend\index.html"

:: -------------------------------------------------------
:: VIRTUAL ENVIRONMENT (Optional)
:: Set USE_VENV=1 to create and use isolated Python environment
:: Set VENV_NAME to change virtual environment folder name
:: -------------------------------------------------------
set "USE_VENV=0"
set "VENV_NAME=venv"

:: ============================================================
::  DO NOT MODIFY BELOW THIS LINE (Unless you know what you're doing)
:: ============================================================

echo.
echo ============================================================
echo    BHAVYA HEALTH DATA FETCHER
echo    Bihar State Health System Performance
echo ============================================================
echo.
echo Project Directory: %PROJECT_DIR%
echo.

:: ============================================================
::  KILL OLD PROCESSES (Prevents conflicts with cached code)
:: ============================================================
echo [CLEANUP] Stopping any existing server processes...
echo ------------------------------------------------------------
taskkill /F /IM python.exe >nul 2>&1
echo [OK] Cleanup complete
echo.

:: Navigate to project directory
cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo [ERROR] Could not navigate to project directory!
    echo Check if the path exists: %PROJECT_DIR%
    pause
    exit /b 1
)

:: Clear Python cache to ensure fresh code is loaded
if exist "backend\__pycache__" (
    echo   Clearing Python cache...
    rmdir /s /q "backend\__pycache__" >nul 2>&1
)

:: ============================================================
::  STEP 1: CHECK PYTHON INSTALLATION
:: ============================================================
echo [STEP 1] Checking Python installation...
echo ------------------------------------------------------------

%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.8 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%i in ('%PYTHON_EXE% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found

:: Check Python version is 3.8+
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if %PY_MAJOR% LSS 3 (
    echo [ERROR] Python 3.8+ is required. You have Python %PYTHON_VERSION%
    pause
    exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 8 (
    echo [ERROR] Python 3.8+ is required. You have Python %PYTHON_VERSION%
    pause
    exit /b 1
)
echo [OK] Python version is compatible
echo.

:: ============================================================
::  STEP 2: SETUP VIRTUAL ENVIRONMENT (OPTIONAL)
:: ============================================================
if "%USE_VENV%"=="1" (
    echo [STEP 2] Setting up virtual environment...
    echo ------------------------------------------------------------

    if not exist "%VENV_NAME%\Scripts\activate.bat" (
        echo Creating virtual environment...
        %PYTHON_EXE% -m venv %VENV_NAME%
        if errorlevel 1 (
            echo [ERROR] Failed to create virtual environment!
            pause
            exit /b 1
        )
        echo [OK] Virtual environment created
    ) else (
        echo [OK] Virtual environment already exists
    )

    :: Activate virtual environment
    call "%VENV_NAME%\Scripts\activate.bat"
    set "PYTHON_EXE=python"
    echo [OK] Virtual environment activated
    echo.
)

:: ============================================================
::  STEP 3: CHECK AND INSTALL REQUIRED PACKAGES
:: ============================================================
echo [STEP 3] Checking and installing required packages...
echo ------------------------------------------------------------

:: Upgrade pip first
echo Upgrading pip...
%PYTHON_EXE% -m pip install --upgrade pip -q 2>nul
echo [OK] pip is up to date
echo.

:: Define required packages
set "PACKAGES=fastapi uvicorn mysql-connector-python python-dotenv requests urllib3 pydantic"

:: Check and install each package
for %%p in (%PACKAGES%) do (
    echo Checking %%p...
    %PYTHON_EXE% -c "import importlib; importlib.import_module('%%p'.replace('-', '_').split('[')[0])" 2>nul
    if errorlevel 1 (
        echo   Installing %%p...
        %PYTHON_EXE% -m pip install %%p -q
        if errorlevel 1 (
            echo   [WARNING] Failed to install %%p
        ) else (
            echo   [OK] %%p installed
        )
    ) else (
        echo   [OK] %%p already installed
    )
)
echo.

:: Install from requirements.txt for exact versions
echo Installing from requirements.txt...
if exist "requirements.txt" (
    %PYTHON_EXE% -m pip install -r requirements.txt -q 2>nul
    echo [OK] All dependencies installed from requirements.txt
) else (
    echo [WARNING] requirements.txt not found, using individually installed packages
)
echo.

:: ============================================================
::  STEP 4: CHECK CONFIGURATION FILE
:: ============================================================
echo [STEP 4] Checking configuration...
echo ------------------------------------------------------------

if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] .env file not found. Creating from .env.example...
        copy ".env.example" ".env" >nul
        echo [WARNING] .env file created from template!
        echo.
        echo *** IMPORTANT: Please edit .env file with your credentials ***
        echo.
        echo Required settings:
        echo   - DB_HOST     : Your MySQL database host
        echo   - DB_USER     : Database username
        echo   - DB_PASSWORD : Database password
        echo   - DB_NAME     : Database name
        echo   - API_SECRET_KEY : Bhavya API secret key
        echo   - API_CLIENT_KEY : Bhavya API client key
        echo.
        echo Press any key to open .env file for editing...
        pause >nul
        notepad ".env"
        echo.
        echo After editing, save the file and press any key to continue...
        pause >nul
    ) else (
        echo [ERROR] Neither .env nor .env.example found!
        echo Please create a .env file with the required configuration.
        pause
        exit /b 1
    )
) else (
    echo [OK] .env file found
)
echo.

:: ============================================================
::  STEP 5: VERIFY DATABASE CONNECTION
:: ============================================================
echo [STEP 5] Verifying database connection...
echo ------------------------------------------------------------

%PYTHON_EXE% -c "from dotenv import load_dotenv; import os; load_dotenv(); import mysql.connector; c=mysql.connector.connect(host=os.getenv('DB_HOST'),user=os.getenv('DB_USER'),password=os.getenv('DB_PASSWORD'),database=os.getenv('DB_NAME'),connection_timeout=10); print('[OK] Database connected successfully'); c.close()" 2>nul
if errorlevel 1 (
    echo [WARNING] Database connection failed!
    echo.
    echo Possible issues:
    echo   - Check your .env file credentials
    echo   - Verify database server is running
    echo   - Check your internet/network connection
    echo   - Ensure the database exists
    echo.
    echo Press any key to continue anyway ^(server will start but may have issues^)...
    pause >nul
)
echo.

:: ============================================================
::  STEP 6: START THE SERVER
:: ============================================================
echo [STEP 6] Starting FastAPI backend server...
echo ------------------------------------------------------------
echo.
echo Server URL:    http://%SERVER_HOST%:%SERVER_PORT%
echo API Docs:      http://%SERVER_HOST%:%SERVER_PORT%/docs
echo Frontend:      %FRONTEND_PATH%
echo.
echo Press Ctrl+C to stop the server
echo.

:: Open browser after delay (frontend is now served at root URL)
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://%SERVER_HOST%:%SERVER_PORT%"

:: ============================================================
::  SERVER LOGS
:: ============================================================
echo ============================================================
echo    SERVER LOGS (Press Ctrl+C to stop)
echo ============================================================
echo.

%PYTHON_EXE% -m uvicorn %BACKEND_APP% --host %SERVER_HOST% --port %SERVER_PORT% --reload

:: ============================================================
::  SERVER STOPPED
:: ============================================================
echo.
echo ============================================================
echo    SERVER STOPPED
echo ============================================================
echo.

if "%USE_VENV%"=="1" (
    call "%VENV_NAME%\Scripts\deactivate.bat" 2>nul
)

echo Press any key to exit...
pause >nul
exit /b 0
