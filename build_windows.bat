@echo off
:: ============================================================
:: J.A.R.V.I.S. Windows Build Script
:: If Windows blocked this file, right-click → Properties
:: → check "Unblock" → OK, then run again.
:: OR just use build_windows.ps1 instead (recommended).
:: ============================================================

:: Self-unblock this script and project files
powershell -Command "Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File" >nul 2>&1

title J.A.R.V.I.S. Build System
color 0B

echo.
echo  ==========================================
echo   J.A.R.V.I.S. Windows Build System
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Download from: https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: Check/create venv
if not exist ".venv" (
    echo  [*] Creating virtual environment...
    python -m venv .venv
)

echo  [*] Activating virtual environment...
call .venv\Scripts\activate.bat

echo  [*] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo  [*] Installing dependencies...
pip install -r requirements.txt --quiet

echo  [*] Installing PyInstaller...
pip install pyinstaller --quiet

echo  [*] Installing Windows audio support...
pip install pyaudio --quiet 2>nul

if not exist "assets" mkdir assets

echo.
echo  [*] Building Jarvis.exe ...
echo.

pyinstaller jarvis.spec --noconfirm --clean 2>&1

echo.
if exist "dist\Jarvis.exe" (
    :: Unblock the built exe so Windows doesn't block it either
    powershell -Command "Unblock-File -Path '.\dist\Jarvis.exe'" >nul 2>&1

    echo  ==========================================
    echo   BUILD SUCCESSFUL
    echo  ==========================================
    echo.
    echo   Executable: dist\Jarvis.exe
    echo.
    echo   First run will download the AI model (~5GB).
    echo   After that, Jarvis starts instantly.
    echo.
    echo   To run:  double-click dist\Jarvis.exe
    echo   Or:      dist\Jarvis.exe --text
    echo.
    echo   If Windows still blocks the .exe:
    echo   Right-click Jarvis.exe ^> Properties ^> Unblock ^> OK
    echo.
) else (
    echo  ==========================================
    echo   BUILD FAILED - See errors above
    echo  ==========================================
    echo.
    echo  Common fixes:
    echo   - Run as Administrator
    echo   - pip install pyaudio
    echo   - pip install --upgrade pyinstaller
    echo.
)

pause
