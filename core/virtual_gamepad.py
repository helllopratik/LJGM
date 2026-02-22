from evdev import UInput, ecodes, AbsInfo


class VirtualGamepad:

    def __init__(self):
        self.ui = None
        self.create()

    def create(self):

        capabilities = {

            ecodes.EV_KEY: [
                ecodes.BTN_A,
                ecodes.BTN_B,
                ecodes.BTN_X,
                ecodes.BTN_Y,
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
            ],

            ecodes.EV_ABS: {
                ecodes.ABS_X:  AbsInfo(0, -32768, 32767, 0, 0, 0),
                ecodes.ABS_Y:  AbsInfo(0, -32768, 32767, 0, 0, 0),
                ecodes.ABS_RX: AbsInfo(0, -32768, 32767, 0, 0, 0),
                ecodes.ABS_RY: AbsInfo(0, -32768, 32767, 0, 0, 0),
                ecodes.ABS_HAT0X: AbsInfo(0, -1, 1, 0, 0, 0),
                ecodes.ABS_HAT0Y: AbsInfo(0, -1, 1, 0, 0, 0),
            }
        }

        self.ui = UInput(
            capabilities,
            name="LJGM Virtual Gamepad",
            vendor=0x1234,
            product=0x5678,
            version=0x0001,
            bustype=ecodes.BUS_USB
        )

    def emit_key(self, code, value):
        self.ui.write(ecodes.EV_KEY, code, value)
        self.ui.syn()

    def emit_abs(self, code, value):
        self.ui.write(ecodes.EV_ABS, code, value)
        self.ui.syn()
