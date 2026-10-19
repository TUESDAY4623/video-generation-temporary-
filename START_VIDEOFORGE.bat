@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "BACKEND=%ROOT%videoforge-backend"
set "FRONTEND=%ROOT%videoforge-studio"
set "FFMPEG_BIN=%BACKEND%\bin"
set "PYTHON=python"
set "NPM=npm"
set "DOCKER=docker"

if exist "%FFMPEG_BIN%" set "PATH=%FFMPEG_BIN%;%PATH%"


echo.
echo  ========================================
echo    VideoForge - AI Video Studio Launcher
echo  ========================================
echo.

echo  [1/5] Checking prerequisites...

where %PYTHON% >nul 2>&1
if errorlevel 1 (
    echo    X Python not found. Install Python 3.11+ from python.org
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do echo    - %%i

where %NPM% >nul 2>&1
if errorlevel 1 (
    echo    X Node.js/npm not found. Install from nodejs.org
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('%NPM% --version 2^>^&1') do echo    - npm %%i

where %DOCKER% >nul 2>&1
if errorlevel 1 (
    echo    X Docker not found. Install Docker Desktop
    pause & exit /b 1
)

ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo    X FFmpeg not found
    pause & exit /b 1
)
echo    - ffmpeg OK

echo    OK All prerequisites found
echo.

echo  [2/5] Configuring backend...

if exist "%BACKEND%\.env" (
    echo    OK .env already exists
) else (
    if exist "%BACKEND%\.env.example" (
        copy /Y "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
        echo    OK .env created from template
        echo.
        echo    IMPORTANT: Edit %BACKEND%\.env and add your ANTHROPIC_API_KEY
        echo    Press any key when ready, or Ctrl+C to exit
        pause >nul
        echo.
    ) else (
        echo    X .env.example not found in: %BACKEND%
        pause & exit /b 1
    )
)

echo.

echo  [3/5] Checking backend dependencies...

if not exist "%BACKEND%\.installed" (
    echo    Installing Python packages - first run, may take a few minutes...
    pushd "%BACKEND%"
    %PYTHON% -m pip install -e ".[dev]" --quiet
    if errorlevel 1 (
        echo    X Backend install failed
        popd & pause & exit /b 1
    )
    break > "%BACKEND%\.installed"
    popd
    echo    OK Backend dependencies installed
) else (
    echo    OK Backend dependencies ready
)

echo.

echo  [4/5] Checking frontend dependencies...

if not exist "%FRONTEND%\node_modules" (
    echo    Installing Node.js packages - first run, may take a few minutes...
    pushd "%FRONTEND%"
    %NPM% install --silent
    if errorlevel 1 (
        echo    X Frontend install failed
        popd & pause & exit /b 1
    )
    popd
    echo    OK Frontend dependencies installed
) else (
    echo    OK Frontend dependencies ready
)

echo.

echo  [5/5] Starting services...
echo.

set "STYLETTS2_AVAILABLE=0"
if exist "%ROOT%ElevenLabs\StyleTTS2\api.py" (
    set "STYLETTS2_AVAILABLE=1"
)

echo    Starting PostgreSQL and Redis...
%DOCKER% compose -f "%BACKEND%\docker-compose.yml" up -d postgres redis >nul 2>&1

echo    Waiting for PostgreSQL...
:wait_pg
%PYTHON% -c "import socket; s=socket.socket(); s.settimeout(1); r=s.connect_ex(('localhost',5432)); s.close(); exit(r)" 2>nul
if errorlevel 1 (
    ping 127.0.0.1 -n 2 >nul
    goto wait_pg
)
echo      OK PostgreSQL ready

echo    Waiting for Redis...
:wait_redis
%PYTHON% -c "import socket; s=socket.socket(); s.settimeout(1); r=s.connect_ex(('localhost',6379)); s.close(); exit(r)" 2>nul
if errorlevel 1 (
    ping 127.0.0.1 -n 2 >nul
    goto wait_redis
)
echo      OK Redis ready

echo.
echo    Starting VideoForge backend...
start "VideoForge-Backend" cmd /C "title VideoForge-Backend && cd /d "%BACKEND%" && "%PYTHON%" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo    Waiting for backend API...
:wait_backend
%PYTHON% -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/health', timeout=1); r.close()" 2>nul
if errorlevel 1 (
    ping 127.0.0.1 -n 3 >nul
    goto wait_backend
)
echo      OK Backend running at http://localhost:8000

if !STYLETTS2_AVAILABLE! equ 1 (
    echo.
    echo    Starting StyleTTS2 - local TTS engine...
    start "VideoForge-StyleTTS2" cmd /C "title VideoForge-StyleTTS2 && cd /d "%ROOT%ElevenLabs\StyleTTS2" && "%PYTHON%" api.py"
    echo      OK StyleTTS2 starting at http://localhost:8000
) else (
    echo.
    echo    WARN StyleTTS2 not found!
    echo         Using Edge-TTS / ElevenLabs cloud provider
)

echo.
echo    Starting VideoForge Studio (frontend)...
start "VideoForge-Frontend" cmd /C "title VideoForge-Frontend && cd /d "%FRONTEND%" && %NPM% run dev"

echo    Waiting for frontend...
:wait_frontend
%PYTHON% -c "import urllib.request; r=urllib.request.urlopen('http://localhost:5173', timeout=1); r.close()" 2>nul
if errorlevel 1 (
    ping 127.0.0.1 -n 3 >nul
    goto wait_frontend
)
echo      OK Frontend running at http://localhost:5173

echo.
echo  ========================================
echo    All services are running!
echo  ========================================
echo.
echo    Frontend Studio   http://localhost:5173
echo    Backend API       http://localhost:8000
echo    API Docs          http://localhost:8000/docs
if !STYLETTS2_AVAILABLE! equ 1 (
    echo    StyleTTS2 - TTS   http://localhost:8000
)
echo.
echo    Press any key or Ctrl+C to stop all services.
echo.

ping 127.0.0.1 -n 3 >nul
start http://localhost:5173

pause >nul

echo.
echo  Shutting down services...

taskkill /FI "WINDOWTITLE eq VideoForge-Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq VideoForge-Frontend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq VideoForge-StyleTTS2*" /T /F >nul 2>&1

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

%DOCKER% compose -f "%BACKEND%\docker-compose.yml" down >nul 2>&1

echo    OK All services stopped
echo.
endlocal
exit /b 0
