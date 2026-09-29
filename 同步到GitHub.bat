@echo off
rem NOTE: keep this file pure ASCII. cmd.exe parses .bat in the system ANSI
rem codepage, so non-ASCII text here gets garbled. Chinese messages are
rem printed by tools\sync.py instead.
chcp 65001 >nul
cd /d "%~dp0"

set PYEXE=py
where py >nul 2>nul || set PYEXE=python

%PYEXE% "tools\sync.py"

echo.
pause
