#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ljgm"
PKG_NAME="ljgm"
VERSION="${1:-1.0.0}"
ARCH="$(dpkg --print-architecture)"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/${PKG_NAME}_${VERSION}_${ARCH}"
PKG_ROOT="${BUILD_DIR}/${PKG_NAME}"
DIST_DIR="${ROOT_DIR}/dist"

rm -rf "${BUILD_DIR}"
mkdir -p \
  "${PKG_ROOT}/DEBIAN" \
  "${PKG_ROOT}/opt/${APP_NAME}" \
  "${PKG_ROOT}/usr/bin" \
  "${PKG_ROOT}/usr/share/applications" \
  "${PKG_ROOT}/usr/share/icons/hicolor/256x256/apps" \
  "${PKG_ROOT}/usr/share/doc/${PKG_NAME}"

cat > "${PKG_ROOT}/DEBIAN/control" <<CONTROL
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: LJGM Team <support@local>
Depends: python3 (>= 3.10), python3-pyqt6, python3-evdev, python3-uinput
Description: Linux Joypad Generic Manager
 GUI tool to map physical gamepads to virtual devices,
 with optional mouse mode and vibration testing.
CONTROL

cat > "${PKG_ROOT}/DEBIAN/postinst" <<'POSTINST'
#!/usr/bin/env bash
set -e
modprobe uinput || true
echo "uinput" > /etc/modules-load.d/ljgm.conf
POSTINST

cat > "${PKG_ROOT}/DEBIAN/prerm" <<'PRERM'
#!/usr/bin/env bash
set -e
if [ -f /etc/modules-load.d/ljgm.conf ]; then
    rm -f /etc/modules-load.d/ljgm.conf
fi
PRERM

chmod 0755 "${PKG_ROOT}/DEBIAN/postinst" "${PKG_ROOT}/DEBIAN/prerm"

rsync -a \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude 'build/' \
  --exclude 'dist/' \
  --exclude '.venv/' \
  --exclude '*.pyc' \
  "${ROOT_DIR}/" "${PKG_ROOT}/opt/${APP_NAME}/"

cat > "${PKG_ROOT}/usr/bin/${APP_NAME}" <<'BIN'
#!/usr/bin/env bash
exec /usr/bin/python3 /opt/ljgm/gui_app.py "$@"
BIN
chmod 0755 "${PKG_ROOT}/usr/bin/${APP_NAME}"

install -m 0644 "${ROOT_DIR}/packaging/ljgm.desktop" "${PKG_ROOT}/usr/share/applications/ljgm.desktop"
install -m 0644 "${ROOT_DIR}/assets/joystick.png" "${PKG_ROOT}/usr/share/icons/hicolor/256x256/apps/ljgm.png"
install -m 0644 "${ROOT_DIR}/README.md" "${PKG_ROOT}/usr/share/doc/${PKG_NAME}/README.md"
install -m 0644 "${ROOT_DIR}/LICENSE" "${PKG_ROOT}/usr/share/doc/${PKG_NAME}/copyright"

dpkg-deb --build "${PKG_ROOT}"
mkdir -p "${DIST_DIR}"
mv "${PKG_ROOT}.deb" "${DIST_DIR}/${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo "Created: ${DIST_DIR}/${PKG_NAME}_${VERSION}_${ARCH}.deb"
