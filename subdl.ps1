# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SubDL — One-liner installer & runner (Windows)
# Usage: irm https://raw.githubusercontent.com/awpetrik/SubDL/main/subdl.ps1 | iex
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$ErrorActionPreference = "Stop"

$REPO_RAW = "https://raw.githubusercontent.com/awpetrik/SubDL/main"
$INSTALL_DIR = Join-Path $env:USERPROFILE ".subdl"
$SCRIPT_NAME = "subdl.py"
$REQUIREMENTS = "requests"
$MIN_PYTHON_MAJOR = 3
$MIN_PYTHON_MINOR = 9

function Write-Info  { param($msg) Write-Host "i  $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "⚠  $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "❌ $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "+--------------------------------------------- +" 
Write-Host "|    SubSource Sub Downloader by awpetrik      |"
Write-Host "|  Download subtitle Indonesia secara instan   |"
Write-Host "|     https://github.com/awpetrik/SubDL        |"
Write-Host "+----------------------------------------------+"
Write-Host ""

# ── Step 1: Check Python ──
Write-Info "Mengecek Python..."

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $versionOutput = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($versionOutput) {
            $parts = $versionOutput.Split(".")
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if ($major -ge $MIN_PYTHON_MAJOR -and $minor -ge $MIN_PYTHON_MINOR) {
                $pythonCmd = $cmd
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $pythonCmd) {
    Write-Fail @"
Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ tidak ditemukan.

  Install Python terlebih dahulu:
    Windows : https://python.org/downloads
              (Centang 'Add Python to PATH' saat install!)
    winget  : winget install Python.Python.3.12
    choco   : choco install python
"@
}

$pythonVersion = & $pythonCmd --version 2>&1
Write-Ok "Python ditemukan: $pythonCmd ($pythonVersion)"

# ── Step 2: Create install directory ──
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
}

# ── Step 3: Setup virtual environment ──
$VENV_DIR = Join-Path $INSTALL_DIR ".venv"
$useVenv = $true

if (-not (Test-Path $VENV_DIR)) {
    Write-Info "Membuat virtual environment..."
    try {
        & $pythonCmd -m venv $VENV_DIR 2>$null
    } catch {
        Write-Warn "venv tidak tersedia. Menggunakan pip langsung..."
        $useVenv = $false
    }
}

if ($useVenv -and (Test-Path $VENV_DIR)) {
    $pythonCmd = Join-Path $VENV_DIR "Scripts\python.exe"
    $pipCmd = Join-Path $VENV_DIR "Scripts\pip.exe"
    Write-Ok "Virtual environment siap."
} else {
    $pipCmd = "$pythonCmd -m pip"
    $useVenv = $false
}

# ── Step 4: Install dependencies ──
Write-Info "Mengecek dependencies..."

$hasRequests = $false
try {
    & $pythonCmd -c "import requests, rich" 2>$null
    if ($LASTEXITCODE -eq 0) { $hasRequests = $true }
} catch {}

if (-not $hasRequests) {
    Write-Info "Menginstall requests rich..."
    try {
        if ($useVenv) {
            & $pipCmd install --quiet $REQUIREMENTS 2>$null
        } else {
            & $pythonCmd -m pip install --quiet $REQUIREMENTS 2>$null
        }
        Write-Ok "Dependency 'requests' terinstall."
    } catch {
        Write-Fail "Gagal install dependency 'requests'. Coba manual: pip install requests rich"
    }
} else {
    Write-Ok "Dependency sudah lengkap."
}

# ── Step 5: Download subdl.py ──
Write-Info "Mendownload SubDL..."

$scriptUrl = "$REPO_RAW/$SCRIPT_NAME"
$scriptPath = Join-Path $INSTALL_DIR $SCRIPT_NAME

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $scriptUrl -OutFile $scriptPath -UseBasicParsing
    Write-Ok "SubDL terinstall di: $scriptPath"
} catch {
    Write-Fail "Gagal download $SCRIPT_NAME dari GitHub."
}

# ── Step 6: Create launcher batch file ──
$launcherBat = Join-Path $INSTALL_DIR "subdl.bat"
$batContent = @"
@echo off
set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%subdl.py" %*
) else (
    python "%SCRIPT_DIR%subdl.py" %*
)
"@
Set-Content -Path $launcherBat -Value $batContent -Encoding ASCII

# ── Step 7: Add to PATH (suggest) ──
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 
Write-Ok "Instalasi selesai!"
Write-Host ""
Write-Host "  Jalankan sekarang:"
Write-Host "    $launcherBat"
Write-Host ""
Write-Host "  Atau tambahkan ke PATH (PowerShell admin):"
Write-Host "    `$oldPath = [Environment]::GetEnvironmentVariable('PATH', 'User')"
Write-Host "    [Environment]::SetEnvironmentVariable('PATH', `"`$oldPath;$INSTALL_DIR`", 'User')"
Write-Host "    subdl   # langsung bisa!"
Write-Host ""
Write-Host "  Jangan lupa set API key:"
Write-Host '    $env:SUBSOURCE_API_KEY="your_key_here"'
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# ── Step 8: Run immediately ──
Write-Host "🚀 Menjalankan SubDL..."
Write-Host ""
& $pythonCmd $scriptPath
