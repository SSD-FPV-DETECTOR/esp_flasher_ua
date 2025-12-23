#!/usr/bin/env bash

./linux_setup_gui.sh

SYSTEM_PYTHON_EXE=python
VENV_NAME=esp_flasher_ua_venv
VENV_PYTHON_EXE=$VENV_NAME/bin/python

"$VENV_PYTHON_EXE" esp_flasher_ua.py --gui
