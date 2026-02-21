from evdev import UInput, ecodes, AbsInfo


class VirtualGamepad:

    def __init__(self):
        self.device = None
        self.create()

    def create(self):

        capabilities = {
            ecodes.EV_KEY: [
                ecodes.BTN_SOUTH,     # A
                ecodes.BTN_EAST,      # B
                ecodes.BTN_NORTH,     # X
                ecodes.BTN_WEST,      # Y
                ecodes.BTN_TL,
                ecodes.BTN_TR,
                ecodes.BTN_TL2,
                ecodes.BTN_TR2,
                ecodes.BTN_SELECT,
                ecodes.BTN_START,
                ecodes.BTN_THUMBL,
                ecodes.BTN_THUMBR,
            ],

            ecodes.EV_ABS: [
                (ecodes.ABS_X,  AbsInfo(0, -32768, 32767, 0, 0, 0)),
                (ecodes.ABS_Y,  AbsInfo(0, -32768, 32767, 0, 0, 0)),
                (ecodes.ABS_RX, AbsInfo(0, -32768, 32767, 0, 0, 0)),
                (ecodes.ABS_RY, AbsInfo(0, -32768, 32767, 0, 0, 0)),
                (ecodes.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0)),
                (ecodes.ABS_HAT0Y, AbsInfo(0, -1, 1, 0, 0, 0)),
            ]
        }

        self.device = UInput(
            capabilities,
            name="LJGM Virtual Gamepad",
            vendor=0x045e,
            product=0x028e,
            version=1,
            bustype=0x03
        )

    def emit_button(self, code, value):
        self.device.write(ecodes.EV_KEY, code, value)
        self.device.syn()

    def emit_axis(self, code, value):
        self.device.write(ecodes.EV_ABS, code, value)
        self.device.syn()