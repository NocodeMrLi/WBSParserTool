$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

if (-not (Test-Path ".\dist\WBSParserTool.exe")) {
    Write-Host "App exe missing, building app first..."
    & ".\build_exe.ps1"
}

& ".\.venv\Scripts\pyinstaller.exe" `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name WBSParserTool-Setup `
    --icon "assets\app_icon.ico" `
    --add-data "assets;assets" `
    --add-data "dist\WBSParserTool.exe;payload\WBSParserTool" `
    installer.py

Write-Host "Build complete: $ProjectRoot\dist\WBSParserTool-Setup.exe"
