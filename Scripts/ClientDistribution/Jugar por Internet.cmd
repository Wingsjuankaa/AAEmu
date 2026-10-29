@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Configurar-Playit.ps1"
if errorlevel 1 (
  pause
  exit /b 1
)
start "" "%~dp0AAEmu-Simple-Launcher-Portable-0.2.1-x64.exe"
