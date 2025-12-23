setlocal

set VENV_NAME=esp_flasher_ua_venv
set VENV_PYTHON_EXE=%VENV_NAME%\Scripts\python.exe

%VENV_PYTHON_EXE% esp_flasher_ua.py %*