# core/vibration.py

from evdev import InputDevice, ecodes, ff
from evdev import list_devices
from core.device_detector import DeviceDetector


class VibrationManager:

    def __init__(self):
        self.device = self.find_device()
        self.enabled = True
        self.intensity = 100   # percent
        self.duration = 1000   # milliseconds

    def find_device(self, preferred_path=None):
        primary = DeviceDetector().find(preferred_path=preferred_path)
        if primary and ecodes.EV_FF in primary.capabilities():
            return primary

        for path in list_devices():
            dev = InputDevice(path)
            if ecodes.EV_FF in dev.capabilities():
                return dev
        return None

    def set_device_path(self, path):
        self.device = self.find_device(preferred_path=path)

    def set_enabled(self, state: bool):
        self.enabled = state

    def set_intensity(self, percent: int):
        self.intensity = max(0, min(100, percent))

    def set_duration(self, ms: int):
        self.duration = max(100, ms)

    def _convert_intensity(self):
        # 0–100% → 0–0xffff
        return int((self.intensity / 100) * 0xffff)

    def test(self, motor="both"):

        if not self.enabled:
            return

        if not self.device:
            print("No vibration device found.")
            return

        strong = 0
        weak = 0
        magnitude = self._convert_intensity()

        if motor == "left":
            strong = magnitude
        elif motor == "right":
            weak = magnitude
        elif motor == "both":
            strong = magnitude
            weak = magnitude

        rumble = ff.Rumble(
            strong_magnitude=strong,
            weak_magnitude=weak
        )

        effect = ff.Effect(
            ecodes.FF_RUMBLE,
            -1,
            0,
            ff.Trigger(0, 0),
            ff.Replay(self.duration, 0),
            ff.EffectType(ff_rumble_effect=rumble)
        )

        effect_id = self.device.upload_effect(effect)
        self.device.write(ecodes.EV_FF, effect_id, 1)
