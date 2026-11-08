@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul || (echo 没找到 Python，请先安装 Python 3：https://www.python.org/downloads/ 安装时勾选 Add python.exe to PATH & pause & exit /b 1)
set /p GAME=请把游戏文件夹拖到这个窗口里，然后按回车：
python -X utf8 patch.py %GAME%
pause
