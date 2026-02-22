import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QSlider,
    QCheckBox, QTextEdit, QLineEdit,
    QFormLayout, QRadioButton, QButtonGroup,
    QTextEdit, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from core.device_detector import DeviceDetector
from core.virtual_gamepad import VirtualGamepad
from core.processor import InputProcessor
from core.vibration import VibrationManager
from core.mapper import Mapper
from gui.mapping_wizard import MappingWizard


# ==========================
# Controller Service Thread
# ==========================


class ControllerThread(QThread):

    status_signal = pyqtSignal(str)

    def __init__(self, vid, pid, keyset_mode="analog"):
        super().__init__()
        self.vid = vid
        self.pid = pid
        self.keyset_mode = keyset_mode
        self.running = False

    def run(self):

        detector = DeviceDetector(vid=self.vid, pid=self.pid)
        device = detector.find()

        if not device:
            self.status_signal.emit("Device Not Found")
            return

        self.status_signal.emit("Running")

        virtual = VirtualGamepad()
        processor = InputProcessor(device, virtual)
        processor.current_mode = self.keyset_mode

        self.running = True
        processor.start()

    def stop(self):
        self.terminate()
        self.wait()


# ==========================
# Main GUI
# ==========================

class LJGM(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("LJGM - Linux Joypad Generic Manager")
        self.setMinimumSize(1200, 800)

        self.thread = None
        self.vibration = VibrationManager()
        # Default empty VID/PID (not hardcoded)
        self.current_vid = ""
        self.current_pid = ""

        self.selected_device = None  # 🔹 central device reference

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.dashboard = self.dashboard_tab()
        self.assign_tab = MappingWizard()
        self.vibration_tab_widget = self.vibration_tab()
        self.advanced_tab_widget = self.advanced_tab()

        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.assign_tab, "Assign")
        self.tabs.addTab(self.vibration_tab_widget, "Vibration")
        self.tabs.addTab(self.advanced_tab_widget, "Advanced")

        self.refresh_device_info()

    # 🔹 Disable Assign + Vibration if no device detected
        if not self.selected_device:
            self.tabs.setTabEnabled(1, False)  # Assign
            self.tabs.setTabEnabled(2, False)  # Vibration

    # ======================
    # Dashboard
    # ======================

    def dashboard_tab(self):

        widget = QWidget()
        layout = QVBoxLayout()

        self.device_label = QLabel()
        self.status_label = QLabel()
        

        self.start_btn = QPushButton("Start Service")
        self.stop_btn = QPushButton("Stop Service")

        self.start_btn.setStyleSheet("background-color: green; color: white;")
        self.stop_btn.setStyleSheet("background-color: red; color: white;")

        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_service)
        self.stop_btn.clicked.connect(self.stop_service)

        # Sensitivity
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(1, 200)
        self.sensitivity_slider.setValue(100)
        self.sensitivity_slider.setEnabled(False)

        self.apply_sensitivity_btn = QPushButton("Apply Sensitivity")
        self.apply_sensitivity_btn.setEnabled(False)
        self.apply_sensitivity_btn.clicked.connect(self.apply_sensitivity)

        # Mouse mode
        self.mouse_checkbox = QCheckBox("Use Left Stick as Mouse")
        self.mouse_checkbox.setEnabled(False)

        # Active mapping mode for runtime processing
        self.active_mode_select = QComboBox()
        self.active_mode_select.addItems(["analog", "digital"])
        self.active_mode_select.setCurrentText("analog")

        layout.addWidget(self.device_label)
        layout.addWidget(self.status_label)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(QLabel("Active Keyset Mode"))
        layout.addWidget(self.active_mode_select)

        layout.addWidget(QLabel("Stick Sensitivity"))
        layout.addWidget(self.sensitivity_slider)
        layout.addWidget(self.apply_sensitivity_btn)
        layout.addWidget(self.mouse_checkbox)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def start_service(self):
    
        if not self.selected_device:
            return

        if self.thread and self.thread.isRunning():
            return

        self.thread = ControllerThread(
            format(self.selected_device.info.vendor, "04x"),
            format(self.selected_device.info.product, "04x"),
            self.active_mode_select.currentText()
        )

        self.thread.status_signal.connect(self.update_status)
        self.thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.sensitivity_slider.setEnabled(True)
        self.apply_sensitivity_btn.setEnabled(True)
        self.mouse_checkbox.setEnabled(True)
    def stop_service(self):

        if self.thread:
            self.thread.stop()

        self.update_status("Not Running")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.sensitivity_slider.setEnabled(False)
        self.apply_sensitivity_btn.setEnabled(False)
        self.mouse_checkbox.setEnabled(False)

    def update_status(self, status):

        if status == "Running":
            self.status_label.setText("Status: 🟢 Running")
        else:
            self.status_label.setText("Status: 🔴 " + status)

    def apply_sensitivity(self):
        value = self.sensitivity_slider.value()
        print("Applying sensitivity:", value)
        # integrate with processor later

    def refresh_device_info(self):
    
        vid = self.vid_input.text().strip() if hasattr(self, "vid_input") else ""
        pid = self.pid_input.text().strip() if hasattr(self, "pid_input") else ""

        detector = DeviceDetector(vid=vid or None, pid=pid or None)
        device = detector.find()

        if device:
            self.selected_device = device

            actual_vid = format(device.info.vendor, "04x")
            actual_pid = format(device.info.product, "04x")

            self.device_label.setText(
                f"Device: {device.name} | VID: {actual_vid} | PID: {actual_pid}"
            )
            self.status_label.setText("Status: 🔴 Not Running")

            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

            self.tabs.setTabEnabled(1, True)
            self.tabs.setTabEnabled(2, True)

        else:
            self.selected_device = None

            self.device_label.setText("Device: Not Detected")
            self.status_label.setText("Status: 🔴 Not Running")

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

            self.sensitivity_slider.setEnabled(False)
            self.apply_sensitivity_btn.setEnabled(False)
            self.mouse_checkbox.setEnabled(False)

            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabEnabled(2, False)

    # ======================
    # Vibration
    # ======================

    def vibration_tab(self):

        widget = QWidget()
        layout = QVBoxLayout()

        self.enable_vibration = QCheckBox("Enable Vibration")
        self.enable_vibration.setChecked(True)
        self.enable_vibration.stateChanged.connect(
            lambda s: self.vibration.set_enabled(s == 2)
        )
        motor_layout = QHBoxLayout()
        self.left_motor = QRadioButton("Left (Strong)")
        self.right_motor = QRadioButton("Right (Weak)")
        self.both_motor = QRadioButton("Both")
        self.both_motor.setChecked(True)
        motor_layout.addWidget(self.left_motor)
        motor_layout.addWidget(self.right_motor)
        motor_layout.addWidget(self.both_motor)
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_slider.setValue(100)
        self.intensity_slider.valueChanged.connect(
            lambda v: self.vibration.set_intensity(v)
        )

        self.duration_slider = QSlider(Qt.Orientation.Horizontal)
        self.duration_slider.setRange(100, 5000)
        self.duration_slider.setValue(1000)
        self.duration_slider.valueChanged.connect(
            lambda v: self.vibration.set_duration(v)
        )
        
        test_btn = QPushButton("Test Vibration")
        test_btn.clicked.connect(self.test_vibration)
        

        layout.addWidget(self.enable_vibration)
        layout.addLayout(motor_layout)
        layout.addWidget(QLabel("Intensity"))
        layout.addWidget(self.intensity_slider)
        layout.addWidget(QLabel("Duration (ms)"))
        layout.addWidget(self.duration_slider)
        layout.addWidget(test_btn)
        layout.addStretch()

        widget.setLayout(layout)
        return widget
    def test_vibration(self):
        if self.left_motor.isChecked():
            motor = "left"
        elif self.right_motor.isChecked():
            motor = "right"
        else:
            motor = "both"

        self.vibration.test(motor)

    # ======================
    # Advanced
    # ======================

    def advanced_tab(self):

        widget = QWidget()
        layout = QVBoxLayout()

        form = QFormLayout()

        self.vid_input = QLineEdit(self.current_vid)
        self.pid_input = QLineEdit(self.current_pid)

        apply_btn = QPushButton("Apply VID/PID")
        apply_btn.clicked.connect(self.apply_vid_pid)

        form.addRow("VID:", self.vid_input)
        form.addRow("PID:", self.pid_input)
        form.addRow(apply_btn)

        self.lsusb_output = QTextEdit()
        self.lsusb_output.setReadOnly(True)

        layout.addLayout(form)
        layout.addWidget(QLabel("Connected USB Devices"))
        layout.addWidget(self.lsusb_output)

        widget.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_lsusb)
        self.timer.start(3000)

        self.refresh_lsusb()

        return widget

    def apply_vid_pid(self):

        self.refresh_device_info()

    def refresh_lsusb(self):
        try:
            result = subprocess.check_output(["lsusb"]).decode()
            self.lsusb_output.setText(result)
        except Exception as e:
            self.lsusb_output.setText(str(e))


def run_app():
    app = QApplication(sys.argv)
    mapper = Mapper()
    window = MappingWizard() if mapper.is_empty() else LJGM()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
