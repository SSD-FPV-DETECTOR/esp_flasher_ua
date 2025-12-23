#!/usr/bin/env bash

SYSTEM_PYTHON_EXE=python
VENV_NAME=esp_flasher_ua_venv
VENV_PYTHON_EXE=$VENV_NAME/bin/python

if [ ! -d "$VENV_NAME" ]; then
	echo "creating VENV..."
	"$SYSTEM_PYTHON_EXE" -m venv "$VENV_NAME"
fi


echo "Installing dependencies into VENV..."
"$VENV_PYTHON_EXE" -m pip install -r requirements.txt

