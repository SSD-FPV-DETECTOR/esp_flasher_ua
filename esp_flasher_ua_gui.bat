setlocal

pushd %~dp0

call setup.bat

@echo Setup script finished

set VENV_NAME=esp_flasher_ua_venv

set VENV_PYTHON_EXE=%VENV_NAME%\Scripts\python.exe

%VENV_PYTHON_EXE% esp_flasher_ua.py --gui

@IF %ERRORLEVEL% NEQ 0 (
	@echo Error
	pause
	exit /b 1
) else (
	@echo Success.
)