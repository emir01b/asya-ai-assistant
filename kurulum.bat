@echo off
setlocal
cd /d "%~dp0"
where pwsh.exe >nul 2>nul
if errorlevel 1 (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0kurulum.ps1" %*
) else (
    pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0kurulum.ps1" %*
)
set "ASYA_SETUP_EXIT=%ERRORLEVEL%"
echo.
if not "%ASYA_SETUP_EXIT%"=="0" echo Kurulum tamamlanamadi. Yukaridaki hata ve indirme baglantilarini kontrol edin.
pause
exit /b %ASYA_SETUP_EXIT%
