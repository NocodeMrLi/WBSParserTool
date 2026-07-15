$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

& ".\.venv\Scripts\pyinstaller.exe" `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name WBSParserTool `
    --icon "assets\app_icon.ico" `
    --hidden-import "ui.main_window" `
    --add-data "prompts;prompts" `
    --add-data "assets;assets" `
    app.py

Write-Host ""
Write-Host "Build complete: $ProjectRoot\dist\WBSParserTool.exe"
