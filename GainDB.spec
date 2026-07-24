# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
#
# PyInstaller build recipe for GainDB (onedir, windowed).
# LGPLv3 compliance: onedir keeps Qt shared libraries as separate files so the
# end user can replace them. Do NOT switch to --onefile.
# License texts are copied into dist/<app>/licenses/ by build_release.ps1.

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

APP_NAME = "GainDB"
ROOT = os.path.abspath(os.getcwd())

# Data files bundled into the app (relative dest keeps them next to the exe tree).
datas = [
    (os.path.join(ROOT, "gui", "assets", "GainDB.png"), os.path.join("gui", "assets")),
    (os.path.join(ROOT, "gui", "translations", "gaindb_ko.qm"), os.path.join("gui", "translations")),
]

# numpy / scipy occasionally need their submodules pulled in explicitly.
hiddenimports = []
hiddenimports += collect_submodules("scipy")
hiddenimports += collect_submodules("numpy")

a = Analysis(
    [os.path.join(ROOT, "gui", "__main__.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed (no console) -> GUI app
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "gui", "assets", "GainDB.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,          # dist/<distpath>/GainDB/ (onedir folder)
)