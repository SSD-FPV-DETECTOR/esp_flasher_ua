VENV_NAME=esp_flasher_ua_venv
PYTHON_EXE=python
if [ ! -d "$VENV_NAME" ]; then
	echo "creating VENV..."
	"$PYTHON_EXE" -m venv "$VENV_NAME"
fi

VENV_PYTHON_EXE=$VENV_NAME/bin/python

echo "Installing dependencies into VENV..."
"$VENV_PYTHON_EXE" -m pip install -r requirements.txt

echo "Installing dependencies for GUI inti VENV..."
"$VENV_PYTHON_EXE" -m pip install -r requirements_gui.txt
REQ_GUI_EXITCODE=$?

if [ "$REQ_GUI_EXITCODE" -ne 0 ]; then
	echo "GUI dependencies failed. Make sure libpcre2-dev installed in system."
	exit 1
fi
