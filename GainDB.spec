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

# We only use scipy.signal.lfilter and numpy. Let PyInstaller's standard
# numpy/scipy hooks pull in the required binaries; do NOT bulk-collect all
# submodules (that dragged in scipy.optimize/sparse/stats/... unnecessarily).
hiddenimports = []

a = Analysis(
    [os.path.join(ROOT, "gui", "__main__.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "PyQt5", "PyQt6",
        # Qt modules we do not use (Widgets-only app). Safe to drop; big savings.
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
        "PySide6.QtWebChannel", "PySide6.QtWebSockets",
        "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2",
        "PySide6.QtQml", "PySide6.QtQmlModels",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
        "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtTest",
        "PySide6.QtSql", "PySide6.QtSvgWidgets", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
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