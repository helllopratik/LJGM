# core/vibration.py

import errno

from evdev import InputDevice, ecodes, ff
from evdev import list_devices
from core.device_detector import DeviceDetector


class VibrationManager:

    def __init__(self):
        self.device = self.find_device()
        self.enabled = True
        self.intensity = 100   # percent
        self.duration = 1000   # milliseconds
        self.effect_id = None

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
        self.effect_id = None

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

        def build_effect(effect_id):
            return ff.Effect(
                ecodes.FF_RUMBLE,
                effect_id,
                0,
                ff.Trigger(0, 0),
                ff.Replay(self.duration, 0),
                ff.EffectType(ff_rumble_effect=rumble)
            )

        # Reuse the previously allocated effect slot to avoid ENOSPC on devices
        # with a very small number of FF effect slots.
        target_effect_id = self.effect_id if self.effect_id is not None else -1
        effect = build_effect(target_effect_id)

        try:
            effect_id = self.device.upload_effect(effect)
        except OSError as exc:
            if exc.errno == errno.ENOSPC and self.effect_id is not None:
                # If kernel state got out of sync, reset and retry once.
                self.effect_id = None
                effect = build_effect(-1)
                effect_id = self.device.upload_effect(effect)
            else:
                raise

        self.effect_id = effect_id
        self.device.write(ecodes.EV_FF, effect_id, 1)
