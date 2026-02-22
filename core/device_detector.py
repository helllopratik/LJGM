from evdev import InputDevice, list_devices, ecodes


class DeviceDetector:

    def __init__(self, vid=None, pid=None):
        self.vid = vid.lower() if vid else None
        self.pid = pid.lower() if pid else None

    GAMEPAD_KEYS = {
        ecodes.BTN_A,
        ecodes.BTN_B,
        ecodes.BTN_X,
        ecodes.BTN_Y,
        ecodes.BTN_SOUTH,
        ecodes.BTN_EAST,
        ecodes.BTN_NORTH,
        ecodes.BTN_WEST,
        ecodes.BTN_TL,
        ecodes.BTN_TR,
        ecodes.BTN_TL2,
        ecodes.BTN_TR2,
        ecodes.BTN_SELECT,
        ecodes.BTN_START,
        ecodes.BTN_THUMBL,
        ecodes.BTN_THUMBR,
        ecodes.BTN_DPAD_UP,
        ecodes.BTN_DPAD_DOWN,
        ecodes.BTN_DPAD_LEFT,
        ecodes.BTN_DPAD_RIGHT,
    }

    GAMEPAD_AXES = {
        ecodes.ABS_X,
        ecodes.ABS_Y,
        ecodes.ABS_RX,
        ecodes.ABS_RY,
        ecodes.ABS_Z,
        ecodes.ABS_RZ,
        ecodes.ABS_HAT0X,
        ecodes.ABS_HAT0Y,
    }

    # Linux generic joystick/gamepad button code ranges.
    JOYSTICK_BUTTON_MIN = 0x120  # BTN_JOYSTICK / BTN_TRIGGER
    JOYSTICK_BUTTON_MAX = 0x13f  # BTN_DIGI end of game/joystick section

    def _score_device(self, dev):
        caps = dev.capabilities(absinfo=True)
        key_codes = set(caps.get(ecodes.EV_KEY, []))
        raw_abs_codes = caps.get(ecodes.EV_ABS, [])
        abs_codes = {
            item[0] if isinstance(item, tuple) else item
            for item in raw_abs_codes
        }

        if not key_codes or not abs_codes:
            return 0

        key_score = len(key_codes & self.GAMEPAD_KEYS)
        generic_joystick_keys = sum(
            1 for code in key_codes
            if self.JOYSTICK_BUTTON_MIN <= code <= self.JOYSTICK_BUTTON_MAX
        )
        key_score += generic_joystick_keys
        axis_score = len(abs_codes & self.GAMEPAD_AXES)

        if key_score == 0 or axis_score == 0:
            return 0

        return key_score + axis_score

    def _is_joystick(self, dev):
        return self._score_device(dev) > 0

    def list_supported(self):
        devices = [InputDevice(path) for path in list_devices()]

        supported = []
        for dev in devices:
            if self.vid and self.pid:
                vid = format(dev.info.vendor, '04x')
                pid = format(dev.info.product, '04x')
                if vid != self.vid or pid != self.pid:
                    continue
            score = self._score_device(dev)
            if score > 0:
                supported.append((score, dev))

        supported.sort(key=lambda item: item[0], reverse=True)
        return [dev for _, dev in supported]

    def find(self, preferred_path=None):
        devices = [InputDevice(path) for path in list_devices()]

        if preferred_path:
            for dev in devices:
                if dev.path == preferred_path and self._is_joystick(dev):
                    return dev

        #  Manual VID/PID mode
        if self.vid and self.pid:
            for dev in devices:
                vid = format(dev.info.vendor, '04x')
                pid = format(dev.info.product, '04x')

                if vid == self.vid and pid == self.pid:
                    return dev
            return None

        # Auto-detect mode (best scoring gamepad-like input device)
        best = None
        best_score = -1
        for dev in devices:
            score = self._score_device(dev)
            if score > best_score:
                best = dev
                best_score = score

        if best_score > 0:
            return best

        return None
