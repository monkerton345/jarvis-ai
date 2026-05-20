# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for J.A.R.V.I.S.
# Run: pyinstaller jarvis.spec

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(".").resolve()

a = Analysis(
    ['jarvis.py'],
    pathex=[str(ROOT), str(ROOT / 'src')],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        # Core
        'jarvis',
        'jarvis.core',
        'jarvis.config',
        'jarvis.brain.llm',
        'jarvis.brain.personality',
        'jarvis.voice.listener',
        'jarvis.voice.speaker',
        'jarvis.voice.wake_word',
        'jarvis.skills.internet',
        'jarvis.skills.time_skill',
        'jarvis.skills.weather',
        'jarvis.skills.system',
        'jarvis.skills.web',
        'jarvis.skills.timers',
        'jarvis.knowledge.base',
        'jarvis.knowledge.ingest',
        'jarvis.ui.terminal',

        # Third-party
        'faster_whisper',
        'faster_whisper.transcribe',
        'edge_tts',
        'chromadb',
        'chromadb.db.impl.sqlite',
        'sentence_transformers',
        'sentence_transformers.models',
        'duckduckgo_search',
        'duckduckgo_search.duckduckgo_search',
        'sounddevice',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
        'pygame',
        'pygame.mixer',
        'rich',
        'rich.console',
        'rich.panel',
        'rich.text',
        'httpx',
        'httpx._config',
        'psutil',
        'keyboard',
        'bs4',
        'bs4.builder',
        'bs4.builder._html5lib',
        'bs4.builder._lxml',
        'dotenv',
        'huggingface_hub',
        'tokenizers',
        'transformers',
        'onnxruntime',
        'tqdm',
        'pydantic',
        'pydantic.v1',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'notebook',
        'ipython',
        'PIL',
        'tkinter',
        'wx',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Jarvis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,           # Keep console for voice feedback / debug
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/jarvis.ico' if Path('assets/jarvis.ico').exists() else None,
    version_file=None,
)
