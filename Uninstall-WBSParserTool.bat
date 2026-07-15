@echo off
setlocal
set "WBS_DEV_PROJECT_ROOT=%~dp0"
set "WBS_UNINSTALL_PS1=%TEMP%\WBSParserTool_uninstall_%RANDOM%%RANDOM%.ps1"

> "%WBS_UNINSTALL_PS1%" echo $ErrorActionPreference = 'SilentlyContinue'
>> "%WBS_UNINSTALL_PS1%" echo $appName = 'WBSParserTool'
>> "%WBS_UNINSTALL_PS1%" echo $exeName = 'WBSParserTool.exe'
>> "%WBS_UNINSTALL_PS1%" echo $devRoot = [System.IO.Path]::GetFullPath($env:WBS_DEV_PROJECT_ROOT).TrimEnd('\')
>> "%WBS_UNINSTALL_PS1%" echo function Add-InstallDirFromShortcut($path, [System.Collections.Generic.List[string]]$dirs) {
>> "%WBS_UNINSTALL_PS1%" echo   if (Test-Path -LiteralPath $path) {
>> "%WBS_UNINSTALL_PS1%" echo     $ws = New-Object -ComObject WScript.Shell
>> "%WBS_UNINSTALL_PS1%" echo     $s = $ws.CreateShortcut($path)
>> "%WBS_UNINSTALL_PS1%" echo     if ($s.TargetPath -and (Split-Path -Leaf $s.TargetPath) -ieq $exeName) { $dirs.Add((Split-Path -Parent $s.TargetPath)) }
>> "%WBS_UNINSTALL_PS1%" echo   }
>> "%WBS_UNINSTALL_PS1%" echo }
>> "%WBS_UNINSTALL_PS1%" echo function Is-DevProjectDir($dir) {
>> "%WBS_UNINSTALL_PS1%" echo   if (-not $dir) { return $false }
>> "%WBS_UNINSTALL_PS1%" echo   $full = [System.IO.Path]::GetFullPath($dir).TrimEnd('\')
>> "%WBS_UNINSTALL_PS1%" echo   return ($full -ieq $devRoot)
>> "%WBS_UNINSTALL_PS1%" echo }
>> "%WBS_UNINSTALL_PS1%" echo function Clean-InstallDir($dir) {
>> "%WBS_UNINSTALL_PS1%" echo   if (-not $dir -or -not (Test-Path -LiteralPath $dir)) { return }
>> "%WBS_UNINSTALL_PS1%" echo   if (Is-DevProjectDir $dir) { Write-Host "Skip developer project: $dir"; return }
>> "%WBS_UNINSTALL_PS1%" echo   Remove-Item -LiteralPath (Join-Path $dir $exeName) -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo   Remove-Item -LiteralPath (Join-Path $dir 'uninstall.bat') -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo   Remove-Item -LiteralPath (Join-Path $dir 'Uninstall-WBSParserTool.bat') -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo   Remove-Item -LiteralPath (Join-Path $dir '卸载WBS任务拆解工具.bat') -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo   Remove-Item -LiteralPath (Join-Path $dir 'WBSParserTool-Setup.exe') -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo   Remove-Item -LiteralPath (Join-Path $dir 'WBSParserTool_feather_1_0_0.ico') -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo   Get-ChildItem -LiteralPath $dir -Filter 'WBSParserTool_feather*.ico' -ErrorAction SilentlyContinue ^| Remove-Item -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo   if ((Split-Path -Leaf $dir) -ieq $appName) { Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue }
>> "%WBS_UNINSTALL_PS1%" echo   elseif (-not (Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue)) { Remove-Item -LiteralPath $dir -Force -ErrorAction SilentlyContinue }
>> "%WBS_UNINSTALL_PS1%" echo }
>> "%WBS_UNINSTALL_PS1%" echo taskkill /F /IM $exeName ^| Out-Null
>> "%WBS_UNINSTALL_PS1%" echo Start-Sleep -Milliseconds 500
>> "%WBS_UNINSTALL_PS1%" echo $desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) "$appName.lnk"
>> "%WBS_UNINSTALL_PS1%" echo $startShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$appName.lnk"
>> "%WBS_UNINSTALL_PS1%" echo $dirs = [System.Collections.Generic.List[string]]::new()
>> "%WBS_UNINSTALL_PS1%" echo Add-InstallDirFromShortcut $desktopShortcut $dirs
>> "%WBS_UNINSTALL_PS1%" echo Add-InstallDirFromShortcut $startShortcut $dirs
>> "%WBS_UNINSTALL_PS1%" echo if ($env:LOCALAPPDATA) { $dirs.Add((Join-Path $env:LOCALAPPDATA "Programs\$appName")) }
>> "%WBS_UNINSTALL_PS1%" echo Remove-Item -LiteralPath $desktopShortcut -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo Remove-Item -LiteralPath $startShortcut -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo foreach ($dir in ($dirs ^| Select-Object -Unique)) { Clean-InstallDir $dir }
>> "%WBS_UNINSTALL_PS1%" echo Remove-Item -LiteralPath (Join-Path $env:APPDATA $appName) -Recurse -Force -ErrorAction SilentlyContinue
>> "%WBS_UNINSTALL_PS1%" echo if ($env:LOCALAPPDATA) { Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA $appName) -Recurse -Force -ErrorAction SilentlyContinue }
>> "%WBS_UNINSTALL_PS1%" echo if (Get-Command ie4uinit.exe -ErrorAction SilentlyContinue) { ie4uinit.exe -show }
>> "%WBS_UNINSTALL_PS1%" echo Write-Host ''
>> "%WBS_UNINSTALL_PS1%" echo Write-Host 'WBSParserTool uninstall complete.'
>> "%WBS_UNINSTALL_PS1%" echo Write-Host 'Developer project files were not deleted.'

powershell -NoProfile -ExecutionPolicy Bypass -File "%WBS_UNINSTALL_PS1%"
set "WBS_EXIT=%ERRORLEVEL%"
del /f /q "%WBS_UNINSTALL_PS1%" >nul 2>nul
echo.
if "%WBS_EXIT%"=="0" (
  echo Uninstall finished.
) else (
  echo Uninstall finished with warnings. Please check the messages above.
)
echo This file only removes installed app files and app data, not the developer project.
pause
