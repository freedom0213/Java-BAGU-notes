@echo off
rem NOTE: keep this file pure ASCII (see 同步到GitHub.bat for the reason).
chcp 65001 >nul
cd /d "%~dp0"

set PYEXE=py
where py >nul 2>nul || set PYEXE=python

echo.
echo   Local preview: http://127.0.0.1:6018/
echo   Open that URL in your browser. Close this window to stop.
echo.

start "" http://127.0.0.1:6018/
%PYEXE% -m http.server 6018 --bind 127.0.0.1 --directory docs
