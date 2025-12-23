#!/usr/bin/env bash

VENV_NAME=esp_flasher_ua_venv
VENV_PYTHON_EXE=$VENV_NAME/bin/python

"$VENV_PYTHON_EXE" esp_flasher_ua.py "$@"
