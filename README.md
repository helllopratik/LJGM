# LJGM

<p align="center">
  <img src="assets/joystick.png" alt="LJGM" width="220" />
</p>

<p align="center">
  <strong>Linux Joypad Generic Manager</strong><br/>
  Turn almost any controller into a clean virtual gamepad + optional mouse mode, with mapping and vibration control.
</p>

## Highlights

- Modern PyQt6 desktop app with tabbed control center
- Smart controller detection (auto + explicit selection)
- Analog and digital mapping profiles
- Virtual gamepad output through `uinput`
- Optional mouse mode (left stick pointer + mapped clicks)
- Vibration testing with intensity/duration controls
- Desktop launcher support (`.desktop`) with icon
- Debian package build script included

## Project Structure

```text
.
├── main.py                   # Main GUI app logic
├── gui_app.py                # Lightweight launcher
├── core/                     # Input, mapping, virtual pad, vibration
├── gui/                      # Mapping wizard
├── config/profile.json       # Saved mapping profile
├── assets/                   # Icon/image assets
├── packaging/                # Desktop + .deb build files
├── install.sh                # One-command setup
└── requirements.txt          # Python dependencies
```

## Quick Install (Recommended)

```bash
chmod +x install.sh
./install.sh
```

This installs:
- system dependencies (`python3`, `PyQt6`, `evdev`, `uinput`, build libs)
- `uinput` module auto-load on boot
- Python virtual environment and packages
- desktop launcher and icon for the current user

## Run

```bash
.venv/bin/python gui_app.py
```

or launch from your desktop app menu (`LJGM`).

## Build Debian Package

```bash
chmod +x packaging/build_deb.sh
./packaging/build_deb.sh
```

Output will be created under:

```text
dist/ljgm_<version>_amd64.deb
```

## Install Debian Package

```bash
sudo apt install ./ljgm_1.0.0_amd64.deb
```

## Notes

- App uses Linux input devices and usually needs proper `uinput` permissions.
- If your controller is not detected, reconnect it and use **Refresh Controllers**.
- Mapping is stored in `config/profile.json`.

## Discoverability Tags

`linux`, `gamepad`, `joystick`, `controller`, `input-remapper`, `uinput`, `evdev`, `pyqt6`, `virtual-gamepad`, `desktop-app`, `debian`, `ubuntu`, `gaming`, `accessibility`, `open-source`

Suggested GitHub Topics:

`linux-gamepad`, `joystick-mapper`, `input-remapper`, `uinput`, `evdev`, `pyqt6`, `debian-package`

## License

MIT (`LICENSE`)
