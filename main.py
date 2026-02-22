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
from evdev import InputDevice

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

    def __init__(
        self,
        device_path=None,
        vid=None,
        pid=None,
        use_mouse_mode=False,
        stick_sensitivity=100,
        mouse_sensitivity=140,
    ):
        super().__init__()
        self.device_path = device_path
        self.vid = vid
        self.pid = pid
        self.use_mouse_mode = use_mouse_mode
        self.stick_sensitivity = stick_sensitivity
        self.mouse_sensitivity = mouse_sensitivity
        self.processor = None
        self.running = False

    def run(self):
        try:
            device = None
            if self.device_path:
                try:
                    device = InputDevice(self.device_path)
                except Exception:
                    device = None

            if not device:
                detector = DeviceDetector(vid=self.vid, pid=self.pid)
                device = detector.find()

            if not device:
                self.status_signal.emit("Device Not Found")
                return

            self.status_signal.emit("Running")

            virtual = VirtualGamepad()
            self.processor = InputProcessor(device, virtual)
            self.processor.set_mouse_mode(self.use_mouse_mode)
            self.processor.set_stick_sensitivity(self.stick_sensitivity)
            self.processor.set_mouse_sensitivity(self.mouse_sensitivity)

            self.running = True
            self.processor.start()
        except Exception as e:
            self.status_signal.emit(f"Error: {e}")

    def set_mouse_mode(self, enabled):
        self.use_mouse_mode = enabled
        if self.processor:
            self.processor.set_mouse_mode(enabled)

    def set_sensitivity(self, percent):
        self.stick_sensitivity = percent
        if self.processor:
            self.processor.set_stick_sensitivity(percent)

    def set_mouse_sensitivity(self, percent):
        self.mouse_sensitivity = percent
        if self.processor:
            self.processor.set_mouse_sensitivity(percent)

    def stop(self):
        if self.processor:
            self.processor.stop()
        self.wait()


# ==========================
# Main GUI
# ==========================

class LJGM(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("LJGM - Linux Joypad Generic Manager")
        self.setMinimumSize(1200, 800)
        self.apply_dark_theme()

        self.thread = None
        self.vibration = VibrationManager()
        # Default empty VID/PID (not hardcoded)
        self.current_vid = ""
        self.current_pid = ""

        self.selected_device = None  # 🔹 central device reference
        self.available_devices = []

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
        self.update_service_controls(False)

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
        self.mouse_checkbox.stateChanged.connect(self.on_mouse_mode_changed)
        self.mouse_sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.mouse_sensitivity_slider.setRange(20, 300)
        self.mouse_sensitivity_slider.setValue(140)
        self.mouse_sensitivity_slider.setEnabled(False)
        self.mouse_sensitivity_slider.valueChanged.connect(
            self.on_mouse_sensitivity_changed
        )
        self.mouse_sensitivity_label = QLabel("Mouse Sensitivity: 140%")
        self.mouse_guide = QLabel()
        self.mouse_guide.setWordWrap(True)
        self.mouse_guide.hide()

        # Explicit controller selector when multiple gamepads are connected
        self.controller_select = QComboBox()
        self.controller_select.currentIndexChanged.connect(self.on_controller_selected)
        self.refresh_controllers_btn = QPushButton("Refresh Controllers")
        self.refresh_controllers_btn.clicked.connect(self.refresh_device_info)

        layout.addWidget(self.device_label)
        layout.addWidget(self.status_label)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(QLabel("Controller List"))
        layout.addWidget(self.controller_select)
        layout.addWidget(self.refresh_controllers_btn)

        layout.addWidget(QLabel("Stick Sensitivity"))
        layout.addWidget(self.sensitivity_slider)
        layout.addWidget(self.apply_sensitivity_btn)
        layout.addWidget(self.mouse_checkbox)
        layout.addWidget(self.mouse_sensitivity_label)
        layout.addWidget(self.mouse_sensitivity_slider)
        layout.addWidget(self.mouse_guide)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #111317;
                color: #e6e8eb;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid #2a2f37;
                border-radius: 8px;
                padding: 6px;
            }
            QTabBar::tab {
                background: #1b2027;
                border: 1px solid #2a2f37;
                padding: 8px 14px;
                margin-right: 6px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #242b35;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2b3440;
                border: 1px solid #3b4655;
                border-radius: 7px;
                padding: 8px 12px;
                color: #f0f4f8;
            }
            QPushButton:hover:enabled { background-color: #364455; }
            QPushButton:disabled {
                background-color: #1a1f26;
                color: #6e7782;
                border: 1px solid #2a313a;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0f1318;
                border: 1px solid #303844;
                border-radius: 6px;
                padding: 6px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2a313a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
                background: #56a8ff;
            }
        """)

    def update_service_controls(self, running):
        self.start_btn.setEnabled(not running and self.selected_device is not None)
        self.stop_btn.setEnabled(running)
        self.controller_select.setEnabled(not running and bool(self.available_devices))
        self.refresh_controllers_btn.setEnabled(not running)

        self.sensitivity_slider.setEnabled(running)
        self.apply_sensitivity_btn.setEnabled(running)
        self.mouse_checkbox.setEnabled(running)
        self.mouse_sensitivity_slider.setEnabled(
            running and self.mouse_checkbox.isChecked()
        )

        if running:
            self.start_btn.setStyleSheet("background-color: #1a1f26; color: #6e7782;")
            self.stop_btn.setStyleSheet("background-color: #d04545; color: white;")
        else:
            self.start_btn.setStyleSheet("background-color: #2f8f4e; color: white;")
            self.stop_btn.setStyleSheet("background-color: #1a1f26; color: #6e7782;")

    def start_service(self):
    
        if not self.selected_device:
            return

        if self.thread and self.thread.isRunning():
            return

        self.thread = ControllerThread(
            device_path=self.selected_device.path,
            vid=format(self.selected_device.info.vendor, "04x"),
            pid=format(self.selected_device.info.product, "04x"),
            use_mouse_mode=self.mouse_checkbox.isChecked(),
            stick_sensitivity=self.sensitivity_slider.value(),
            mouse_sensitivity=self.mouse_sensitivity_slider.value(),
        )

        self.thread.status_signal.connect(self.update_status)
        self.thread.start()
        self.update_service_controls(True)
        if self.mouse_checkbox.isChecked():
            self.update_mouse_guide()
    def stop_service(self):

        if self.thread:
            self.thread.stop()
            self.thread = None

        self.update_status("Not Running")
        self.update_service_controls(False)

    def on_mouse_mode_changed(self, state):
        enabled = state == 2
        self.mouse_sensitivity_slider.setEnabled(
            enabled and self.thread and self.thread.isRunning()
        )
        self.mouse_guide.setVisible(enabled)
        if enabled:
            self.update_mouse_guide()
        if self.thread and self.thread.isRunning():
            self.thread.set_mouse_mode(enabled)
            self.thread.set_mouse_sensitivity(self.mouse_sensitivity_slider.value())

    def on_mouse_sensitivity_changed(self, value):
        self.mouse_sensitivity_label.setText(f"Mouse Sensitivity: {value}%")
        if self.thread and self.thread.isRunning():
            self.thread.set_mouse_sensitivity(value)

    def update_status(self, status):
    
        if status == "Running":
            self.status_label.setText("Status: 🟢 Running")
        else:
            self.status_label.setText("Status: 🔴 " + status)
            if status.startswith("Error"):
                self.update_service_controls(False)

    def apply_sensitivity(self):
        value = self.sensitivity_slider.value()
        if self.thread and self.thread.isRunning():
            self.thread.set_sensitivity(value)
            self.status_label.setText(f"Status: 🟢 Running (Stick Sensitivity {value}%)")
        else:
            self.status_label.setText(f"Status: 🔴 Not Running (Stick Sensitivity {value}%)")

    def _binding_for_virtual(self, virtual_name):
        data = Mapper().data
        analog = data.get("analog", {}).get("buttons", {})
        digital = data.get("digital", {}).get("buttons", {})

        analog_key = next((p for p, v in analog.items() if v == virtual_name), None)
        digital_key = next((p for p, v in digital.items() if v == virtual_name), None)

        if analog_key and digital_key:
            if analog_key == digital_key:
                return analog_key
            return f"analog:{analog_key} | digital:{digital_key}"
        if analog_key:
            return f"analog:{analog_key}"
        if digital_key:
            return f"digital:{digital_key}"
        return "not assigned"

    def update_mouse_guide(self):
        guide_lines = [
            "Mouse Guide (auto mode from analog/digital bindings):",
            "Cursor Move: Left Stick (D-Pad also moves cursor if controller emits HAT)",
            f"Left Click: {self._binding_for_virtual('BTN_A')} -> BTN_A",
            f"Right Click: {self._binding_for_virtual('BTN_B')} -> BTN_B",
            f"Double Click: {self._binding_for_virtual('BTN_X')} -> BTN_X",
            f"Middle Click: {self._binding_for_virtual('BTN_Y')} -> BTN_Y",
            f"Scroll Up: {self._binding_for_virtual('BTN_TL')} -> BTN_TL",
            f"Scroll Down: {self._binding_for_virtual('BTN_TR')} -> BTN_TR",
        ]
        self.mouse_guide.setText("\n".join(guide_lines))

    def refresh_device_info(self):
        self.refresh_controller_list()

    def refresh_controller_list(self):
        vid = self.vid_input.text().strip() if hasattr(self, "vid_input") else ""
        pid = self.pid_input.text().strip() if hasattr(self, "pid_input") else ""
        previous_path = self.selected_device.path if self.selected_device else None

        detector = DeviceDetector(vid=vid or None, pid=pid or None)
        devices = detector.list_supported()
        if not devices and (vid or pid):
            # Fall back to full auto-list when VID/PID filter gives no matches.
            devices = DeviceDetector().list_supported()

        self.available_devices = devices

        self.controller_select.blockSignals(True)
        self.controller_select.clear()
        for dev in devices:
            actual_vid = format(dev.info.vendor, "04x")
            actual_pid = format(dev.info.product, "04x")
            label = f"{dev.name} ({actual_vid}:{actual_pid}) [{dev.path}]"
            self.controller_select.addItem(label, dev.path)
        self.controller_select.blockSignals(False)

        if not devices:
            self.selected_device = None
            self.assign_tab.set_controller_path(None)
            self.vibration.set_device_path(None)
            self.device_label.setText("Device: Not Detected")
            self.status_label.setText("Status: 🔴 Not Running")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.update_service_controls(False)
            self.mouse_checkbox.setChecked(False)
            self.mouse_guide.hide()
            self.controller_select.setEnabled(False)
            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabEnabled(2, False)
            return

        self.controller_select.setEnabled(True)
        self.update_service_controls(False)
        target_index = 0
        if previous_path:
            for idx, dev in enumerate(devices):
                if dev.path == previous_path:
                    target_index = idx
                    break

        self.controller_select.setCurrentIndex(target_index)
        self.set_selected_device(devices[target_index])
        self.stop_btn.setEnabled(False)

    def on_controller_selected(self, index):
        if index < 0 or index >= len(self.available_devices):
            return
        self.set_selected_device(self.available_devices[index])

    def set_selected_device(self, device):
        self.selected_device = device
        actual_vid = format(device.info.vendor, "04x")
        actual_pid = format(device.info.product, "04x")
        self.device_label.setText(
            f"Device: {device.name} | VID: {actual_vid} | PID: {actual_pid}"
        )
        self.status_label.setText("Status: 🔴 Not Running")
        self.start_btn.setEnabled(True)
        self.tabs.setTabEnabled(1, True)
        self.tabs.setTabEnabled(2, True)
        self.assign_tab.set_controller_path(device.path)
        self.vibration.set_device_path(device.path)
        if self.mouse_checkbox.isChecked():
            self.update_mouse_guide()

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
