# =============================================================================
# VideoForge - One-Click Launcher (PowerShell)
# =============================================================================

$ErrorActionPreference = "Stop"

$ROOT_DIR = $PSScriptRoot
$BACKEND = Join-Path $ROOT_DIR "videoforge-backend"
$FRONTEND = Join-Path $ROOT_DIR "videoforge-studio"
$PYTHON = "python"
$NPM = "npm"
$DOCKER = "docker"

$procs = @()

function Write-Step($msg) {
    Write-Host ""
    Write-Host "  [${msg}]" -ForegroundColor Yellow
}

function Write-Ok($msg) {
    Write-Host "    OK ${msg}" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "    X ${msg}" -ForegroundColor Red
}

function Wait-Port($port, $label, $timeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", $port)
            $tcp.Close()
            Write-Ok "${label} ready on port ${port}"
            return $true
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    Write-Fail "${label} did not start on port ${port} within ${timeoutSec}s"
    return $false
}

# ── Header ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "    VideoForge - AI Video Studio Launcher" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check prerequisites ─────────────────────────────────────────────
Write-Step "1/5 Checking prerequisites"

try {
    $v = & $PYTHON --version 2>&1
    Write-Host "    - ${v}"
} catch {
    Write-Fail "Python not found. Install Python 3.11+ from python.org"
    pause; exit 1
}

try {
    $v = & $NPM --version 2>&1
    Write-Host "    - npm ${v}"
} catch {
    Write-Fail "Node.js/npm not found. Install from nodejs.org"
    pause; exit 1
}

try {
    $v = & $DOCKER --version 2>&1
    Write-Host "    - ${v}"
} catch {
    Write-Fail "Docker not found. Install Docker Desktop"
    pause; exit 1
}

$ffmpegBin = Join-Path $BACKEND "bin\ffmpeg.exe"
if (-not (Test-Path $ffmpegBin)) {
    Write-Fail "FFmpeg not found at ${ffmpegBin}"
    pause; exit 1
}
Write-Host "    - ffmpeg OK"
Write-Ok "All prerequisites found"
Write-Host ""

# ── Step 2: Configure backend .env ──────────────────────────────────────────
Write-Step "2/5 Configuring backend"

$envPath = Join-Path $BACKEND ".env"
$envExamplePath = Join-Path $BACKEND ".env.example"

if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath -Force
        Write-Ok ".env created from template"
        Write-Host ""
        Write-Host "    IMPORTANT: Edit ${envPath} and add your ANTHROPIC_API_KEY" -ForegroundColor Cyan
        Write-Host "    Press any key when ready, or Ctrl+C to exit" -ForegroundColor Cyan
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        Write-Host ""
    } else {
        Write-Fail ".env.example not found in: ${BACKEND}"
        pause; exit 1
    }
} else {
    Write-Ok ".env already exists"
}
Write-Host ""

# ── Step 3: Install backend dependencies ────────────────────────────────────
Write-Step "3/5 Checking backend dependencies"

$installedMarker = Join-Path $BACKEND ".installed"
if (-not (Test-Path $installedMarker)) {
    Write-Host "    Installing Python packages (first run, may take a few minutes)..."
    Push-Location $BACKEND
    try {
        & $PYTHON -m pip install -e ".[dev]" 2>&1 | ForEach-Object { Write-Host "      $_" }
        New-Item -Path $installedMarker -ItemType File -Force | Out-Null
        Write-Ok "Backend dependencies installed"
    } catch {
        Write-Fail "Backend install failed"
        Pop-Location
        pause; exit 1
    }
    Pop-Location
} else {
    Write-Ok "Backend dependencies ready"
}
Write-Host ""

# ── Step 4: Install frontend dependencies ───────────────────────────────────
Write-Step "4/5 Checking frontend dependencies"

$nodeModules = Join-Path $FRONTEND "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "    Installing Node.js packages (first run, may take a few minutes)..."
    Push-Location $FRONTEND
    try {
        & $NPM install --silent 2>&1 | Out-Null
        Write-Ok "Frontend dependencies installed"
    } catch {
        Write-Fail "Frontend install failed"
        Pop-Location
        pause; exit 1
    }
    Pop-Location
} else {
    Write-Ok "Frontend dependencies ready"
}
Write-Host ""

# ── Step 5: Start services ──────────────────────────────────────────────────
Write-Step "5/5 Starting services"
Write-Host ""

# Check StyleTTS2
$styletts2Available = $false
$styletts2Path = Join-Path $ROOT_DIR "ElevenLabs\StyleTTS2\api.py"
if (Test-Path $styletts2Path) {
    $styletts2Available = $true
}

# Start Docker (PostgreSQL + Redis)
Write-Host "    Starting PostgreSQL and Redis..."
$dockerArgs = "compose --project-directory ""$BACKEND"" up -d postgres redis"
$dockerProc = Start-Process -FilePath $DOCKER -ArgumentList $dockerArgs -NoNewWindow -PassThru
$procs += $dockerProc

# Wait for PostgreSQL
if (-not (Wait-Port 5432 "PostgreSQL" 30)) {
    Write-Fail "PostgreSQL did not start"
    & $DOCKER compose --project-directory "$BACKEND" logs postgres 2>&1 | Write-Host
    pause; exit 1
}

# Wait for Redis
if (-not (Wait-Port 6379 "Redis" 30)) {
    Write-Fail "Redis did not start"
    pause; exit 1
}

# Start backend (uvicorn)
Write-Host ""
Write-Host "    Starting VideoForge backend..."
$backendProc = Start-Process -FilePath $PYTHON -ArgumentList "-m","uvicorn","main:app","--host","0.0.0.0","--port","8000","--reload" -WorkingDirectory $BACKEND -WindowStyle Normal -PassThru
$procs += $backendProc

if (-not (Wait-Port 8000 "Backend API" 30)) {
    Write-Fail "Backend did not start"
    pause; exit 1
}

# Start StyleTTS2 if available
if ($styletts2Available) {
    Write-Host ""
    Write-Host "    Starting StyleTTS2 (local TTS engine)..."
    $ttsProc = Start-Process -FilePath $PYTHON -ArgumentList "api.py" -WorkingDirectory "D:\Coder_S3\video generation v3\ElevenLabs\StyleTTS2" -WindowStyle Normal -PassThru
    $procs += $ttsProc
    Write-Ok "StyleTTS2 starting at http://localhost:8000"
} else {
    Write-Host ""
    Write-Host "    WARN StyleTTS2 not found!" -ForegroundColor Yellow
    Write-Host "         TTS will fail unless you start it manually or configure cloud TTS" -ForegroundColor Yellow
}

# Start frontend (Vite)
Write-Host ""
Write-Host "    Starting VideoForge Studio (frontend)..."
$frontendProc = Start-Process -FilePath $NPM -ArgumentList "run","dev" -WorkingDirectory $FRONTEND -WindowStyle Normal -PassThru
$procs += $frontendProc

if (-not (Wait-Port 5173 "Frontend" 30)) {
    Write-Fail "Frontend did not start"
    pause; exit 1
}

# ── All running ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  +------------------------------------------+" -ForegroundColor Green
Write-Host "    All services are running!" -ForegroundColor Green
Write-Host "  +------------------------------------------+" -ForegroundColor Green
Write-Host ""
Write-Host "    Frontend Studio   http://localhost:5173" -ForegroundColor Cyan
Write-Host "    Backend API       http://localhost:8000" -ForegroundColor Cyan
Write-Host "    API Docs          http://localhost:8000/docs" -ForegroundColor Cyan
if ($styletts2Available) {
    Write-Host "    StyleTTS2 (TTS)   http://localhost:8000" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "    Close this window or press Ctrl+C to stop all services." -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

# ── Wait for user to stop ───────────────────────────────────────────────────
try {
    while ($true) {
        Start-Sleep -Seconds 5
        # Check if any process died
        foreach ($p in $procs) {
            if (-not $p.HasExited) {
                $_.Refresh()
                if ($p.HasExited -and $p.ExitCode -ne 0) {
                    Write-Host ""
                    Write-Fail "Process $($p.ProcessName) exited with code $($p.ExitCode)"
                }
            }
        }
    }
} catch {
    # Ctrl+C pressed
}

# ── Shutdown ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Shutting down services..." -ForegroundColor Yellow

foreach ($p in $procs) {
    if (-not $p.HasExited) {
        $p.CloseMainWindow() | Out-Null
        $p.WaitForExit | Out-Null
        if (-not $p.HasExited) {
            $p.Kill() | Out-Null
        }
    }
}

& $DOCKER compose --project-directory $BACKEND down 2>&1 | Out-Null

Write-Ok "All services stopped"
Write-Host ""
exit 0
