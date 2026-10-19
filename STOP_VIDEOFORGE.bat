@echo off
setlocal

set "BACKEND=%~dp0videoforge-backend"
set "DOCKER=docker"

echo.
echo  Stopping VideoForge services...
echo.

taskkill /FI "WINDOWTITLE eq VideoForge-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq VideoForge-Frontend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq VideoForge-StyleTTS2*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq VideoForge-Docker*" /F >nul 2>&1

if exist "%BACKEND%\docker-compose.yml" (
    echo   Stopping PostgreSQL and Redis...
    %DOCKER% compose -f "%BACKEND%\docker-compose.yml" down >nul 2>&1
)

echo.
echo  All VideoForge services stopped.
echo.
pause
endlocal
exit /b 0
