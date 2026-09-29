@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYEXE=py
where py >nul 2>nul || set PYEXE=python

echo.
echo ============================================
echo   同步笔记到 GitHub
echo   1) 从 Java八股.md 重建站点
echo   2) git 提交
echo   3) 推送到远程仓库
echo ============================================
echo.

%PYEXE% "tools\sync.py"

echo.
pause
