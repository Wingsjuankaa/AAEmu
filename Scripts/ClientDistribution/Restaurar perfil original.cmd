@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Perfil-local.ps1" -Mode Rollback
pause
