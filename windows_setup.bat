setlocal

pushd %~dp0

set SYSTEM_PYTHON_EXE=python
set VENV_NAME=esp_flasher_ua_venv

IF NOT EXIST "%VENV_NAME%" (
	@echo creating VENV...
	%SYSTEM_PYTHON_EXE% -m venv %VENV_NAME%
)

@echo Installing dependencies into VENV...

set VENV_PYTHON_EXE=%VENV_NAME%\Scripts\python.exe

%VENV_PYTHON_EXE% -m pip install -r requirements.txt

@IF %ERRORLEVEL% NEQ 0 (
	@echo Error
	pause
	exit /b 1
) else (
	@echo Success.
)
