@echo off
echo ========================================
echo   Nexus Brain - 安全安装程序 v4.0
echo ========================================
echo.
echo 选择安装模式:
echo   [M] 合并安装 - 保留原有配置，只添加新文件 (推荐)
echo   [O] 覆盖安装 - 完整替换 (会丢失原有配置)
echo   [Q] 退出
echo.
set /p choice=请选择 (M/O/Q):
if /i "%choice%"=="Q" exit
if /i "%choice%"=="M" goto MERGE
if /i "%choice%"=="O" goto OVERWRITE
echo 无效选择，退出
exit

:MERGE
echo.
echo 正在以合并模式启动安装...
echo.
powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0install\install.ps1\" -MergeInstall' -Verb RunAs"
goto END

:OVERWRITE
echo.
echo 正在以覆盖模式启动安装...
echo.
powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0install\install.ps1\" -OverwriteInstall' -Verb RunAs"

:END
pause
