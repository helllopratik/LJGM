#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="LJGM"
APP_ID="ljgm"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
DESKTOP_FILE="${PROJECT_ROOT}/packaging/${APP_ID}.desktop"
ICON_FILE="${PROJECT_ROOT}/assets/joystick.png"

if [[ "${EUID}" -eq 0 ]]; then
    echo "Run this installer as a normal user (it will use sudo when required)."
    exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required."
    exit 1
fi

echo "[1/6] Installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-pyqt6 \
    python3-evdev \
    python3-uinput \
    libevdev-dev \
    libudev-dev \
    udev \
    desktop-file-utils

echo "[2/6] Enabling uinput kernel module..."
echo "uinput" | sudo tee /etc/modules-load.d/ljgm.conf >/dev/null
sudo modprobe uinput

echo "[3/6] Creating / updating Python virtual environment..."
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "${PROJECT_ROOT}/requirements.txt"
deactivate

echo "[4/6] Installing desktop launcher and icon..."
mkdir -p "${HOME}/.local/share/applications" "${HOME}/.local/share/icons/hicolor/256x256/apps"

if [[ -f "${DESKTOP_FILE}" ]]; then
    cp "${DESKTOP_FILE}" "${HOME}/.local/share/applications/${APP_ID}.desktop"
    sed -i "s|Exec=.*|Exec=${PROJECT_ROOT}/.venv/bin/python ${PROJECT_ROOT}/gui_app.py|g" \
        "${HOME}/.local/share/applications/${APP_ID}.desktop"
    sed -i "s|Icon=.*|Icon=${APP_ID}|g" "${HOME}/.local/share/applications/${APP_ID}.desktop"
fi

if [[ -f "${ICON_FILE}" ]]; then
    cp "${ICON_FILE}" "${HOME}/.local/share/icons/hicolor/256x256/apps/${APP_ID}.png"
fi

update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
gtk-update-icon-cache "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo "[5/6] Validating Python dependencies..."
"${VENV_DIR}/bin/python" -c "import PyQt6, evdev, uinput; print('Python dependencies OK')"

echo "[6/6] Installation complete."
echo
echo "Start command:"
echo "  ${PROJECT_ROOT}/.venv/bin/python ${PROJECT_ROOT}/gui_app.py"
echo
echo "Tip: log out/in once if input permissions do not apply immediately."
