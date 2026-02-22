import sys
import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QApplication,
    QComboBox, QPushButton,
    QVBoxLayout, QGridLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer

from evdev import ecodes
from core.device_detector import DeviceDetector
from core.mapper import Mapper


BUTTON_MAP = {
    "1 (Green / Triangle)": "BTN_Y",
    "2 (Red / Circle)": "BTN_B",
    "3 (Blue / Cross)": "BTN_A",
    "4 (Pink / Square)": "BTN_X",
    "L1": "BTN_TL",
    "R1": "BTN_TR",
    "L2": "BTN_TL2",
    "R2": "BTN_TR2",
    "Select": "BTN_SELECT",
    "Start": "BTN_START",
    "L3 (Left Stick Press)": "BTN_THUMBL",
    "R3 (Right Stick Press)": "BTN_THUMBR",
    "D-Pad Up": "BTN_DPAD_UP",
    "D-Pad Down": "BTN_DPAD_DOWN",
    "D-Pad Left": "BTN_DPAD_LEFT",
    "D-Pad Right": "BTN_DPAD_RIGHT",
}


class MappingWizard(QWidget):

    def __init__(self, controller_path=None):
        super().__init__()

        self.setWindowTitle("LJGM - Controller Mapping Wizard")
        self.setFixedSize(900, 660)

        self.mapper = Mapper()
        self.current_mode = "analog"
        self.waiting_for = None
        self.controller_path = controller_path

        self.buttons = {}

        self.setup_ui()
        self.refresh_ui()

        # Setup safe polling instead of threading
        self.joystick = self.detect_joystick()
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_input)
        self.timer.start(10)
        if not self.joystick:
            self.status.setText("No joystick detected")

    # ----------------- UI -----------------

    def setup_ui(self):

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        top_layout = QHBoxLayout()

        self.mode_select = QComboBox()
        self.mode_select.addItems(["analog", "digital"])
        self.mode_select.currentTextChanged.connect(self.change_mode)

        top_layout.addWidget(QLabel("Keyset Mode:"))
        top_layout.addWidget(self.mode_select)
        top_layout.addStretch()

        main_layout.addLayout(top_layout)

        grid = QGridLayout()

        layout_order = [
            ("L2", 0, 0), ("R2", 0, 3),
            ("L1", 1, 0), ("R1", 1, 3),

            ("4 (Pink / Square)", 2, 0), ("1 (Green / Triangle)", 2, 3),
            ("3 (Blue / Cross)", 3, 0), ("2 (Red / Circle)", 3, 3),

            ("Select", 4, 1), ("Start", 4, 2),

            ("L3 (Left Stick Press)", 5, 0),
            ("R3 (Right Stick Press)", 5, 3),
            ("D-Pad Up", 6, 1),
            ("D-Pad Left", 7, 0),
            ("D-Pad Right", 7, 2),
            ("D-Pad Down", 8, 1),
        ]

        for name, row, col in layout_order:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, b=name: self.assign_button(b))
            grid.addWidget(btn, row, col)
            self.buttons[name] = btn

        main_layout.addLayout(grid)

        self.status = QLabel("Click a button to assign")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status)

    # ----------------- Styles -----------------

    def default_style(self):
        return "background-color: #2c2c2c; color: white;"

    def assigned_style(self):
        return "background-color: #1e7f1e; color: white;"

    def waiting_style(self):
        return "background-color: #d81b60; color: white;"

    # ----------------- Logic -----------------

    def detect_joystick(self):
        dev = DeviceDetector().find(preferred_path=self.controller_path)
        if not dev:
            return None
        os.set_blocking(dev.fd, False)
        return dev

    def set_controller_path(self, path):
        self.controller_path = path
        self.waiting_for = None
        self.joystick = self.detect_joystick()
        if self.joystick:
            self.status.setText(f"Controller selected: {self.joystick.name}")
        else:
            self.status.setText("No joystick detected")

    def _extract_physical_token(self, event, virtual_name):
        if event.type == ecodes.EV_KEY and event.value == 1:
            return str(event.code)

        if event.type != ecodes.EV_ABS:
            return None

        # D-pad directions generally come from HAT axis events.
        if virtual_name == "BTN_DPAD_UP" and event.code == ecodes.ABS_HAT0Y and event.value == -1:
            return f"{event.code}:{event.value}"
        if virtual_name == "BTN_DPAD_DOWN" and event.code == ecodes.ABS_HAT0Y and event.value == 1:
            return f"{event.code}:{event.value}"
        if virtual_name == "BTN_DPAD_LEFT" and event.code == ecodes.ABS_HAT0X and event.value == -1:
            return f"{event.code}:{event.value}"
        if virtual_name == "BTN_DPAD_RIGHT" and event.code == ecodes.ABS_HAT0X and event.value == 1:
            return f"{event.code}:{event.value}"

        return None

    def change_mode(self, mode):
        self.current_mode = mode
        self.waiting_for = None
        self.refresh_ui()
        self.status.setText(f"Switched to {mode}")

    def assign_button(self, name):
        self.waiting_for = name
        self.refresh_ui()
        self.buttons[name].setStyleSheet(self.waiting_style())
        self.status.setText(f"Press physical button for {name}")

    def refresh_ui(self):
        self.current_mode = self.mode_select.currentText()

        mode_data = self.mapper.data.get(self.current_mode, {}).get("buttons", {})

        for name, btn in self.buttons.items():

            btn.setText(name)

            assigned = False
            for phys, virt in mode_data.items():
                if virt == BUTTON_MAP[name]:
                    btn.setText(f"{name}\n→ {phys}")
                    btn.setStyleSheet(self.assigned_style())
                    assigned = True
                    break

            if not assigned:
                btn.setStyleSheet(self.default_style())

    def poll_input(self):

        if not self.joystick or not self.waiting_for:
            return

        try:
            for event in self.joystick.read():
                self.current_mode = self.mode_select.currentText()
                virtual_name = BUTTON_MAP[self.waiting_for]
                physical_token = self._extract_physical_token(event, virtual_name)

                if not physical_token:
                    continue

                self.mapper.set_mapping(
                    self.current_mode,
                    physical_token,
                    virtual_name
                )

                self.waiting_for = None
                self.refresh_ui()
                self.status.setText(f"Mapping updated: {physical_token} -> {virtual_name}")
                break

        except BlockingIOError:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MappingWizard()
    window.show()
    sys.exit(app.exec())
