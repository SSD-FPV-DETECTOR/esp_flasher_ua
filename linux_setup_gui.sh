#!/usr/bin/env bash

./linux_setup.sh

SYSTEM_PYTHON_EXE=python
VENV_NAME=esp_flasher_ua_venv
VENV_PYTHON_EXE=$VENV_NAME/bin/python

echo "Installing dependencies for GUI into VENV..."
"$VENV_PYTHON_EXE" -m pip install -r requirements_gui.txt
REQ_GUI_EXITCODE=$?


#TODO: check for pcre bins exist, without installing python-pcre

if [ "$REQ_GUI_EXITCODE" -ne 0 ]; then
	echo "GUI dependencies failed. Make sure libpcre2-dev installed in system."
	exit 1
fi
