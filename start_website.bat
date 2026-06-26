@echo off
cd /d "%~dp0"
echo De website wordt gestart op http://localhost:8000
echo Sluit dit venster om de lokale website te stoppen.
start "" http://localhost:8000
where py >nul 2>nul
if %errorlevel%==0 (
  py -m http.server 8000
) else (
  python -m http.server 8000
)
if errorlevel 1 (
  echo.
  echo Python kon niet worden gestart. Controleer of Python is geinstalleerd.
  pause
)
