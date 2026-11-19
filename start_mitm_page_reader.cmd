@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0start_mitm_page_reader.py"
) else (
    python "%~dp0start_mitm_page_reader.py"
)
if errorlevel 1 (
    echo.
    echo Startup failed. Review the error above.
    pause
)
