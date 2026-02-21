from evdev import InputDevice, list_devices


class DeviceDetector:

    def __init__(self, vid=None, pid=None, name=None):
        self.vid = vid
        self.pid = pid
        self.name = name

    def find(self):
        devices = [InputDevice(path) for path in list_devices()]

        for dev in devices:
            vid = format(dev.info.vendor, '04x')
            pid = format(dev.info.product, '04x')

            if self.vid and self.pid:
                if vid == self.vid and pid == self.pid:
                    return dev

            if self.name and self.name.lower() in dev.name.lower():
                return dev

        return None
