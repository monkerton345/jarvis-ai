# ============================================================
# J.A.R.V.I.S. Windows Build Script (PowerShell)
# Recommended over build_windows.bat — handles SmartScreen
# automatically with no popups.
#
# HOW TO RUN:
#   Right-click build_windows.ps1 → "Run with PowerShell"
#   OR from PowerShell terminal:
#   Set-ExecutionPolicy Bypass -Scope Process; .\build_windows.ps1
# ============================================================

# Always run from the folder this script lives in
Set-Location $PSScriptRoot

# Self-unblock all project files (fixes SmartScreen on scripts)
Write-Host ""
Write-Host "  Unblocking project files..." -ForegroundColor Cyan
Get-ChildItem -Path $PSScriptRoot -Recurse | Unblock-File -ErrorAction SilentlyContinue
Write-Host "  Done." -ForegroundColor Green

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   J.A.R.V.I.S. Windows Build System" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pyver = python --version 2>&1
    Write-Host "  Python: $pyver" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python not found." -ForegroundColor Red
    Write-Host "  Download: https://python.org" -ForegroundColor Yellow
    Write-Host "  Check 'Add Python to PATH' during install." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create/activate venv
if (-not (Test-Path ".venv")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "  Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Install deps
Write-Host "  Installing dependencies..." -ForegroundColor Cyan
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
pip install pyaudio --quiet 2>$null

# Create assets dir
if (-not (Test-Path "assets")) { New-Item -ItemType Directory -Path "assets" | Out-Null }

# Build
Write-Host ""
Write-Host "  Building Jarvis.exe..." -ForegroundColor Cyan
Write-Host ""

pyinstaller jarvis.spec --noconfirm --clean

Write-Host ""
if (Test-Path "dist\Jarvis.exe") {
    # Unblock the .exe so Windows won't block it on first run
    Unblock-File -Path "dist\Jarvis.exe"
    
    # Add a manifest to suppress SmartScreen on the .exe
    Write-Host "  Applying Windows manifest..." -ForegroundColor Cyan
    $manifestContent = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="1.0.0.0" processorArchitecture="amd64"
    name="Jarvis" type="win32"/>
  <description>J.A.R.V.I.S. - Just A Rather Very Intelligent System</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
</assembly>
"@
    $manifestPath = "dist\Jarvis.exe.manifest"
    $manifestContent | Out-File -FilePath $manifestPath -Encoding UTF8

    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Green
    Write-Host "   BUILD SUCCESSFUL" -ForegroundColor Green
    Write-Host "  ==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Executable: dist\Jarvis.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "   First run downloads the AI model (~5GB)." -ForegroundColor Yellow
    Write-Host "   After that, Jarvis starts instantly." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Run: double-click dist\Jarvis.exe" -ForegroundColor White
    Write-Host "   Or:  .\dist\Jarvis.exe --text" -ForegroundColor White
    Write-Host ""
    Write-Host "   If SmartScreen still appears:" -ForegroundColor Yellow
    Write-Host "   Click 'More info' → 'Run anyway'" -ForegroundColor Yellow
    Write-Host "   (This happens because the .exe isn't code-signed)" -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "  ==========================================" -ForegroundColor Red
    Write-Host "   BUILD FAILED — see errors above" -ForegroundColor Red
    Write-Host "  ==========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Common fixes:" -ForegroundColor Yellow
    Write-Host "   - Run PowerShell as Administrator" -ForegroundColor White
    Write-Host "   - pip install pyaudio" -ForegroundColor White
    Write-Host "   - pip install --upgrade pyinstaller" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to close"
