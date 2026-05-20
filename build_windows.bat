@echo off
:: ============================================================
:: J.A.R.V.I.S. Windows Executable Builder
:: Packages Jarvis into a standalone .exe using PyInstaller
:: Run this from the jarvis-ai root folder
:: ============================================================

title Jarvis Build System
color 0B

echo.
echo  ==========================================
echo   J.A.R.V.I.S. Windows Build System
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from python.org
    pause
    exit /b 1
)

:: Check venv
if not exist ".venv" (
    echo  [*] Creating virtual environment...
    python -m venv .venv
)

echo  [*] Activating virtual environment...
call .venv\Scripts\activate.bat

echo  [*] Installing dependencies...
pip install -r requirements.txt --quiet

echo  [*] Installing PyInstaller...
pip install pyinstaller --quiet

echo  [*] Installing Windows audio support...
pip install pyaudio --quiet

:: Create assets dir if needed
if not exist "assets" mkdir assets

:: Download a Jarvis-style icon if not present
if not exist "assets\jarvis.ico" (
    echo  [*] Downloading icon...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/monkerton345/jarvis-ai/main/assets/jarvis.ico' -OutFile 'assets\jarvis.ico' -ErrorAction SilentlyContinue}"
    if not exist "assets\jarvis.ico" (
        echo  [!] Icon download failed - building without custom icon
    )
)

echo.
echo  [*] Building executable...
echo.

:: Run PyInstaller with spec file if it exists, otherwise use defaults
if exist "jarvis.spec" (
    pyinstaller jarvis.spec --noconfirm
) else (
    pyinstaller ^
        --onefile ^
        --name "Jarvis" ^
        --icon "assets\jarvis.ico" ^
        --add-data "src;src" ^
        --add-data ".env.example;." ^
        --hidden-import "faster_whisper" ^
        --hidden-import "edge_tts" ^
        --hidden-import "chromadb" ^
        --hidden-import "sentence_transformers" ^
        --hidden-import "duckduckgo_search" ^
        --hidden-import "sounddevice" ^
        --hidden-import "pygame" ^
        --hidden-import "rich" ^
        --hidden-import "httpx" ^
        --hidden-import "psutil" ^
        --collect-all "faster_whisper" ^
        --collect-all "chromadb" ^
        --collect-all "sentence_transformers" ^
        --collect-all "tokenizers" ^
        --collect-all "transformers" ^
        --console ^
        jarvis.py
)

echo.
if exist "dist\Jarvis.exe" (
    echo  ==========================================
    echo   BUILD SUCCESSFUL
    echo  ==========================================
    echo.
    echo   Executable: dist\Jarvis.exe
    echo.
    echo   HOW TO USE:
    echo   1. Copy dist\Jarvis.exe anywhere you like
    echo   2. Make sure Ollama is running: ollama serve
    echo   3. Double-click Jarvis.exe
    echo      OR run from command line for more options:
    echo         Jarvis.exe --text
    echo         Jarvis.exe --provider openai --model gpt-4o
    echo.
    echo   NOTE: First run will download Whisper model (~150MB)
    echo   and embedding model (~90MB). Subsequent runs are instant.
    echo.
) else (
    echo  ==========================================
    echo   BUILD FAILED
    echo  ==========================================
    echo.
    echo  Check the output above for errors.
    echo  Common fixes:
    echo   - pip install pyaudio  (if audio error)
    echo   - pip install --upgrade pyinstaller
    echo.
)

pause
