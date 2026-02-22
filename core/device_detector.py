from evdev import InputDevice, list_devices, ecodes


class DeviceDetector:

    def __init__(self, vid=None, pid=None):
        self.vid = vid.lower() if vid else None
        self.pid = pid.lower() if pid else None

    def _is_joystick(self, dev):
        caps = dev.capabilities()
        return ecodes.EV_ABS in caps and ecodes.EV_KEY in caps

    def find(self):
        devices = [InputDevice(path) for path in list_devices()]

        #  Manual VID/PID mode
        if self.vid and self.pid:
            for dev in devices:
                vid = format(dev.info.vendor, '04x')
                pid = format(dev.info.product, '04x')

                if vid == self.vid and pid == self.pid:
                    return dev
            return None

        # Auto-detect mode
        for dev in devices:
            if self._is_joystick(dev):
                return dev

        return None