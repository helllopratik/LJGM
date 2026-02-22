import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTabWidget,
    QHBoxLayout
)
from PyQt6.QtCore import QThread, pyqtSignal

from core.device_detector import DeviceDetector
from core.virtual_gamepad import VirtualGamepad
from core.processor import InputProcessor
from gui.mapping_wizard import MappingWizard


TARGET_VID = "0079"
TARGET_PID = "0006"
TARGET_NAME = "Joystick"


# ===============================
# Thread for Input Processor
# ===============================

class ProcessorThread(QThread):

    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.device = None

    def run(self):

        detector = DeviceDetector(
            vid=TARGET_VID,
            pid=TARGET_PID,
            name=TARGET_NAME
        )

        self.device = detector.find()

        if not self.device:
            self.status_signal.emit("No compatible device found.")
            return

        self.status_signal.emit(f"Device Found: {self.device.path}")

        virtual = VirtualGamepad()
        self.status_signal.emit("Virtual Gamepad Created")

        processor = InputProcessor(self.device, virtual)

        self.running = True
        self.status_signal.emit("Forwarding events...")

        try:
            processor.start()
        except Exception as e:
            self.status_signal.emit(str(e))
        finally:
            if self.device:
                self.device.ungrab()
            self.status_signal.emit("Stopped")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


# ===============================
# Main GUI
# ===============================

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("LJGM - Linux Joypad Generic Manager")
        self.setFixedSize(1000, 750)

        self.thread = None

        self.setup_ui()

    # ---------------- UI ----------------

    def setup_ui(self):

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        tabs = QTabWidget()

        # -------- TAB 1: Controller --------
        controller_tab = QWidget()
        controller_layout = QVBoxLayout()
        controller_tab.setLayout(controller_layout)

        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-size: 16px;")

        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Controller")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_controller)

        self.stop_btn = QPushButton("Stop Controller")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self.stop_controller)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)

        controller_layout.addWidget(self.status_label)
        controller_layout.addLayout(button_layout)
        controller_layout.addStretch()

        # -------- TAB 2: Mapping --------
        mapping_tab = MappingWizard()

        tabs.addTab(controller_tab, "Controller")
        tabs.addTab(mapping_tab, "Mapping")

        main_layout.addWidget(tabs)

    # ---------------- Controller Logic ----------------

    def start_controller(self):

        if self.thread and self.thread.isRunning():
            self.status_label.setText("Already Running")
            return

        self.thread = ProcessorThread()
        self.thread.status_signal.connect(self.update_status)
        self.thread.start()

    def stop_controller(self):

        if self.thread:
            self.thread.stop()
            self.status_label.setText("Stopped")

    def update_status(self, text):
        self.status_label.setText(f"Status: {text}")


# ===============================
# App Entry
# ===============================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())