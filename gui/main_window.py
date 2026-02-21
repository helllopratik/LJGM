from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from core.mapper import Mapper
from evdev import InputDevice, list_devices
import threading


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LJGM Mapping Tool")
        self.setGeometry(200, 200, 400, 300)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Click button to map")
        self.layout.addWidget(self.label)

        self.mapper = Mapper()
        self.waiting_for = None

        # Example 4 buttons for now
        for btn_name in ["BTN_A", "BTN_B", "BTN_X", "BTN_Y"]:
            btn = QPushButton(btn_name)
            btn.clicked.connect(lambda checked, b=btn_name: self.start_mapping(b))
            self.layout.addWidget(btn)

        self.listener_thread = threading.Thread(target=self.listen_input, daemon=True)
        self.listener_thread.start()

    def start_mapping(self, button_name):
        self.waiting_for = button_name
        self.label.setText(f"Press physical button for {button_name}")

    def listen_input(self):
        devices = [InputDevice(path) for path in list_devices()]
        joystick = None

        for d in devices:
            if "Joystick" in d.name:
                joystick = d
                break

        if not joystick:
            return

        for event in joystick.read_loop():
            if event.type == 1 and self.waiting_for:
                self.mapper.set_mapping(event.code, self.waiting_for)
                self.mapper.save()
                self.label.setText(f"Mapped {event.code} → {self.waiting_for}")
                self.waiting_for = None
