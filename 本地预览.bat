@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYEXE=py
where py >nul 2>nul || set PYEXE=python

echo.
echo   本地预览地址： http://127.0.0.1:6018/
echo   在浏览器打开上面这个地址即可。
echo   关闭本窗口 = 停止预览。
echo.

start "" http://127.0.0.1:6018/
%PYEXE% -m http.server 6018 --bind 127.0.0.1 --directory docs
