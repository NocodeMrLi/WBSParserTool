from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path


APP_NAME = "WBSParserTool"
EXE_NAME = "WBSParserTool.exe"
ICON_NAME = "WBSParserTool_feather_hd_1_0_0.ico"
UNINSTALL_BAT_NAME = "uninstall.bat"
UNINSTALL_CLEAR_NAME = "卸载WBS任务拆解工具.bat"
UNINSTALL_EN_NAME = "Uninstall-WBSParserTool.bat"


def get_default_install_dir() -> Path:
    existing = find_existing_install_dir()
    if existing:
        return existing

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Programs" / APP_NAME
    return Path.home() / "AppData" / "Local" / "Programs" / APP_NAME


def find_existing_install_dir() -> Path | None:
    candidates = []
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop" / f"{APP_NAME}.lnk"
    start_menu = Path(os.environ.get("APPDATA", str(Path.home()))) / r"Microsoft\Windows\Start Menu\Programs" / f"{APP_NAME}.lnk"
    for shortcut in (desktop, start_menu):
        target = _read_shortcut_target(shortcut)
        if target and target.name.lower() == EXE_NAME.lower():
            candidates.append(target.parent)

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Programs" / APP_NAME)

    for candidate in candidates:
        if (candidate / EXE_NAME).exists():
            return candidate
    return None


def install_application(
    payload_exe: Path,
    target_dir: Path,
    create_shortcut: bool = True,
    icon_source: Path | None = None,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_exe = target_dir / EXE_NAME
    _stop_running_app()
    shutil.copy2(payload_exe, target_exe)
    target_icon = _install_icon(icon_source, target_dir)

    if create_shortcut:
        create_desktop_shortcut(target_exe, target_dir, target_icon)

    write_uninstall_script(target_dir)
    return target_exe


def create_desktop_shortcut(target_exe: Path, workdir: Path, icon_path: Path | None = None) -> None:
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    shortcut_path = desktop / f"{APP_NAME}.lnk"
    _create_shortcut(shortcut_path, target_exe, workdir, icon_path)

    start_menu = Path(os.environ.get("APPDATA", str(Path.home()))) / r"Microsoft\Windows\Start Menu\Programs"
    start_shortcut = start_menu / f"{APP_NAME}.lnk"
    _create_shortcut(start_shortcut, target_exe, workdir, icon_path)


def write_uninstall_script(target_dir: Path) -> None:
    for legacy_name in (UNINSTALL_CLEAR_NAME, UNINSTALL_BAT_NAME):
        legacy_path = target_dir / legacy_name
        if legacy_path.exists():
            legacy_path.unlink()

    uninstall_bat = target_dir / UNINSTALL_EN_NAME
    uninstall_bat.write_text(_uninstall_script_content(), encoding="utf-8-sig")


def _uninstall_script_content() -> str:
    generated_files = [
        EXE_NAME,
        f"{APP_NAME}-Setup.exe",
        ICON_NAME,
        "WBSParserTool_feather_1_0_0.ico",
        UNINSTALL_BAT_NAME,
        UNINSTALL_CLEAR_NAME,
        UNINSTALL_EN_NAME,
    ]
    remove_file_lines = "\n".join(
        f">> \"%WBS_UNINSTALL_PS1%\" echo Remove-Item -LiteralPath (Join-Path $appDir '{name}') -Force -ErrorAction SilentlyContinue"
        for name in generated_files
    )
    content = f"""@echo off
chcp 65001 >nul
setlocal
set "APP_DIR=%~dp0"
set "SELF_PATH=%~f0"
set "WBS_UNINSTALL_PS1=%TEMP%\\WBSParserTool_uninstall_%RANDOM%%RANDOM%.ps1"
set "WBS_SELF_DELETE=%TEMP%\\WBSParserTool_selfdelete_%RANDOM%%RANDOM%.cmd"

> "%WBS_UNINSTALL_PS1%" echo $ErrorActionPreference = 'SilentlyContinue'
>> "%WBS_UNINSTALL_PS1%" echo $appName = '{APP_NAME}'
>> "%WBS_UNINSTALL_PS1%" echo $exeName = '{EXE_NAME}'
>> "%WBS_UNINSTALL_PS1%" echo $appDir = [System.IO.Path]::GetFullPath($env:APP_DIR).TrimEnd('\\')
>> "%WBS_UNINSTALL_PS1%" echo if (-not (Test-Path -LiteralPath (Join-Path $appDir $exeName))) {{ Write-Host 'WBSParserTool is not found in this folder.'; exit 0 }}
>> "%WBS_UNINSTALL_PS1%" echo taskkill /F /IM $exeName ^| Out-Null
>> "%WBS_UNINSTALL_PS1%" echo Start-Sleep -Milliseconds 500
>> "%WBS_UNINSTALL_PS1%" echo Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath('Desktop')) "$appName.lnk") -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo Remove-Item -LiteralPath (Join-Path $env:APPDATA "Microsoft\\Windows\\Start Menu\\Programs\\$appName.lnk") -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo Remove-Item -LiteralPath (Join-Path $env:APPDATA $appName) -Recurse -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo if ($env:LOCALAPPDATA) {{ Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA $appName) -Recurse -Force -ErrorAction SilentlyContinue }}
{remove_file_lines}
>> "%WBS_UNINSTALL_PS1%" echo Get-ChildItem -LiteralPath $appDir -Filter 'WBSParserTool_feather*.ico' -ErrorAction SilentlyContinue ^| Remove-Item -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo $remaining = @(Get-ChildItem -LiteralPath $appDir -Force -ErrorAction SilentlyContinue)
>> "%WBS_UNINSTALL_PS1%" echo if ((Split-Path -Leaf $appDir) -ieq $appName -or $remaining.Count -eq 0) {{ Remove-Item -LiteralPath $appDir -Recurse -Force -ErrorAction SilentlyContinue }}
>> "%WBS_UNINSTALL_PS1%" echo if (Get-Command ie4uinit.exe -ErrorAction SilentlyContinue) {{ ie4uinit.exe -show }}
>> "%WBS_UNINSTALL_PS1%" echo Write-Host 'WBSParserTool uninstall complete.'

powershell -NoProfile -ExecutionPolicy Bypass -File "%WBS_UNINSTALL_PS1%"
set "WBS_EXIT=%ERRORLEVEL%"
del /f /q "%WBS_UNINSTALL_PS1%" >nul 2>nul
echo.
if "%WBS_EXIT%"=="0" (
  echo WBSParserTool uninstall complete.
) else (
  echo WBSParserTool uninstall finished with warnings.
)
echo Only installed app files and app data were removed.
pause

> "%WBS_SELF_DELETE%" echo @echo off
>> "%WBS_SELF_DELETE%" echo timeout /t 1 /nobreak ^>nul
>> "%WBS_SELF_DELETE%" echo del /f /q "%SELF_PATH%" ^>nul 2^>nul
>> "%WBS_SELF_DELETE%" echo rd "%APP_DIR%" ^>nul 2^>nul
>> "%WBS_SELF_DELETE%" echo del /f /q "%%~f0" ^>nul 2^>nul
start "" /min "%WBS_SELF_DELETE%"
endlocal
"""
    return content


def _install_icon(icon_source: Path | None, target_dir: Path) -> Path | None:
    if not icon_source or not icon_source.exists():
        return None
    target_icon = target_dir / ICON_NAME
    shutil.copy2(icon_source, target_icon)
    return target_icon


def _create_shortcut(shortcut_path: Path, target_exe: Path, workdir: Path, icon_path: Path | None) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    icon_location = icon_path if icon_path and icon_path.exists() else target_exe
    shortcut = _ps_string(str(shortcut_path))
    target = _ps_string(str(target_exe))
    working_dir = _ps_string(str(workdir))
    icon = _ps_string(f"{icon_location},0")
    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{shortcut}')
$s.TargetPath = '{target}'
$s.WorkingDirectory = '{working_dir}'
$s.IconLocation = '{icon}'
$s.Save()
"""
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-Command",
            ps_script,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _read_shortcut_target(shortcut_path: Path) -> Path | None:
    if not shortcut_path.exists():
        return None
    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{_ps_string(str(shortcut_path))}')
$s.TargetPath
"""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-Command",
                ps_script,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    target = result.stdout.strip()
    return Path(target) if target else None


def _stop_running_app() -> None:
    subprocess.run(["taskkill", "/F", "/IM", EXE_NAME], check=False, capture_output=True, text=True)
    time.sleep(0.4)


def _ps_string(value: str) -> str:
    return value.replace("'", "''")
