# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
#
# GainDB release build script (Windows / PowerShell).
# - onedir PyInstaller build (LGPLv3-friendly: Qt DLLs stay replaceable).
# - Cleans stale artifacts, builds, then copies & verifies license texts.
#
# Usage (from repo root, inside .venv):
#     .\build_release.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$appName   = "GainDB"
$buildDir  = Join-Path $root "build"
$distDir   = Join-Path $buildDir "dist"          # onedir output -> build\dist\GainDB\
$workDir   = Join-Path $buildDir "pyinstaller"   # PyInstaller work dir
$appDir    = Join-Path $distDir $appName
$licOutDir = Join-Path $appDir "licenses"

Write-Host "=== GainDB release build ===" -ForegroundColor Cyan

# --- 0. environment sanity checks ---------------------------------------------
# Warn if a SYSTEM PySide6 might shadow the venv one (PyInstaller picks system first).
$inVenv = $env:VIRTUAL_ENV -and (Test-Path $env:VIRTUAL_ENV)
if (-not $inVenv) {
    Write-Warning "No active virtual environment detected. Activate .venv first for a reproducible build."
}
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) { throw "PyInstaller not found. Run: pip install pyinstaller" }
python -c "import PySide6" 2>$null
if ($LASTEXITCODE -ne 0) { throw "PySide6 not found in the current environment." }

# --- 1. clean stale artifacts -------------------------------------------------
Write-Host "-- cleaning old artifacts" -ForegroundColor Yellow
foreach ($p in @($buildDir, (Join-Path $root "dist"))) {
    if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}
Get-ChildItem $root -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

# --- 2. build -----------------------------------------------------------------
Write-Host "-- running PyInstaller (onedir)" -ForegroundColor Yellow
pyinstaller "GainDB.spec" --noconfirm --distpath $distDir --workpath $workDir
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
if (-not (Test-Path $appDir)) { throw "Expected app folder not found: $appDir" }

# --- 3. gather license texts --------------------------------------------------
Write-Host "-- copying license texts" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $licOutDir | Out-Null

# 3a. our own license/notice files (must exist in repo root).
$ourFiles = @("LICENSE", "NOTICE", "THIRD_PARTY_LICENSES")
foreach ($f in $ourFiles) {
    $src = Join-Path $root $f
    if (-not (Test-Path $src)) { throw "Missing required license file in repo root: $f" }
    Copy-Item $src (Join-Path $licOutDir $f) -Force
}

# 3b. Qt / PySide6 license texts.
#     Prefer whatever the installed PySide6 ships (future-proof); fall back to the
#     pinned copies in licenses/qt/ (needed for versions that ship no texts, e.g. 6.11.1).
$qtOutDir = Join-Path $licOutDir "qt"
New-Item -ItemType Directory -Force -Path $qtOutDir | Out-Null

$pyside6Dir = python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
$pysideLicDir = Join-Path $pyside6Dir "LICENSES"
$copiedFromPackage = $false
if (Test-Path $pysideLicDir) {
    Write-Host "   found PySide6/LICENSES in package -> copying" -ForegroundColor Green
    Copy-Item (Join-Path $pysideLicDir "*") $qtOutDir -Recurse -Force
    $copiedFromPackage = $true
}

# Always ensure the canonical LGPL/GPL texts are present (pinned repo copies).
$pinnedQt = Join-Path $root "licenses\qt"
foreach ($f in @("LGPL-3.0.txt", "GPL-3.0.txt")) {
    $dest = Join-Path $qtOutDir $f
    if (-not (Test-Path $dest)) {
        $src = Join-Path $pinnedQt $f
        if (-not (Test-Path $src)) { throw "Missing pinned Qt license: licenses\qt\$f" }
        Copy-Item $src $dest -Force
    }
}
if (-not $copiedFromPackage) {
    Write-Host "   PySide6 ships no LICENSES folder -> used pinned licenses\qt\" -ForegroundColor Green
}

# --- 4. verify (fail the build if any license text is missing) -----------------
Write-Host "-- verifying bundled licenses" -ForegroundColor Yellow
$required = @(
    (Join-Path $licOutDir "LICENSE"),
    (Join-Path $licOutDir "NOTICE"),
    (Join-Path $licOutDir "THIRD_PARTY_LICENSES"),
    (Join-Path $qtOutDir  "LGPL-3.0.txt"),
    (Join-Path $qtOutDir  "GPL-3.0.txt")
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    Write-Error "License verification FAILED. Missing:`n$($missing -join "`n")"
    throw "Build aborted: bundled licenses incomplete."
}

Write-Host ""
Write-Host "=== BUILD OK ===" -ForegroundColor Cyan
Write-Host "App:      $appDir"
Write-Host "Licenses: $licOutDir"
Write-Host "Reminder: distribute the WHOLE folder (onedir keeps Qt DLLs replaceable = LGPLv3)." -ForegroundColor DarkCyan