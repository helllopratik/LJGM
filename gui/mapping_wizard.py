import sys
from PyQt6.QtWidgets import (
    QWidget, QLabel, QApplication,
    QComboBox, QPushButton,
    QVBoxLayout, QGridLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer

from evdev import InputDevice, list_devices, ecodes
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
    "R3 (Right Stick Press)": "BTN_THUMBR"
}


class MappingWizard(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("LJGM - Controller Mapping Wizard")
        self.setFixedSize(850, 600)

        self.mapper = Mapper()
        self.current_mode = "analog"
        self.waiting_for = None

        self.buttons = {}

        self.setup_ui()
        self.refresh_ui()

        # Setup safe polling instead of threading
        self.joystick = self.detect_joystick()
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_input)
        self.timer.start(10)

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
        for path in list_devices():
            dev = InputDevice(path)
            if "Joystick" in dev.name:
                return dev
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
                if event.type == ecodes.EV_KEY and event.value == 1:

                    virtual_name = BUTTON_MAP[self.waiting_for]

                    self.mapper.set_mapping(
                        self.current_mode,
                        event.code,
                        virtual_name
                    )

                    self.waiting_for = None
                    self.refresh_ui()
                    self.status.setText("Mapping updated")

        except BlockingIOError:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MappingWizard()
    window.show()
    sys.exit(app.exec())
