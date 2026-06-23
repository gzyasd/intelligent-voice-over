# PyInstaller spec for IVO Python backend
# Build: uv run pyinstaller scripts/build-python.spec --noconfirm --distpath dist/python --workpath dist/python-build
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
project_root = Path(SPECPATH).parent if 'SPECPATH' in globals() else Path.cwd()

# 跨平台 ffmpeg 二进制包含逻辑
ffmpeg_bin_dir = project_root / 'ffmpeg' / 'bin'
ffmpeg_datas: list[tuple[str, str]] = []
if ffmpeg_bin_dir.exists():
    # 包含目录下所有文件（跨平台：Windows 的 .exe/.dll，macOS/Linux 的无扩展名二进制）
    ffmpeg_datas.append((str(ffmpeg_bin_dir), 'ffmpeg/bin'))

a = Analysis(
    [str(project_root / 'scripts' / 'ivo_server_entry.py')],
    pathex=[
        str(project_root / 'src'),
        str(project_root),
    ],
    binaries=[],
    datas=[
        # 包含 examples 目录（profile 模板）
        (str(project_root / 'examples'), 'examples'),
    ] + ffmpeg_datas,
    hiddenimports=(
        [
            'uvicorn.logging',
            'uvicorn.loops',
            'uvicorn.loops.auto',
            'uvicorn.protocols',
            'uvicorn.protocols.http',
            'uvicorn.protocols.http.auto',
            'uvicorn.protocols.websockets',
            'uvicorn.protocols.websockets.auto',
            'uvicorn.lifespan',
            'uvicorn.lifespan.on',
            'fastapi',
            'fastapi.middleware.cors',
            'pydantic',
        ]
        # 自动收集 server 与 ivo 包的所有子模块，避免相对导入/延迟导入在打包后缺失
        + collect_submodules('server')
        + collect_submodules('ivo')
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6',
        'pytest',
        'mypy',
        'ruff',
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
    name='ivo-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
