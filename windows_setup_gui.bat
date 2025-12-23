setlocal

pushd %~dp0

set SYSTEM_PYTHON_EXE=python
set VENV_NAME=esp_flasher_ua_venv
set VENV_PYTHON_EXE=%VENV_NAME%\Scripts\python.exe

call windows_setup.bat

@IF %ERRORLEVEL% NEQ 0 (
	@echo windows_setup.bat Error
	pause
	exit /b 1
)

@echo Installing GUI dependencies into VENV...

%VENV_PYTHON_EXE% -m pip install -r requirements_gui.txt

@IF %ERRORLEVEL% NEQ 0 (
	@echo Error
	pause
	exit /b 1
) else (
	@echo Success.
)
