from evdev import ecodes
from core.mapper import Mapper


class InputProcessor:

    DEADZONE = 4000

    def __init__(self, physical, virtual):
        self.physical = physical
        self.virtual = virtual
        self.mapper = Mapper()
        self.hat_state = {
            ecodes.ABS_HAT0X: 0,
            ecodes.ABS_HAT0Y: 0,
        }

        # For now default mode = analog
        # Later we will auto-detect LED state
        self.current_mode = "analog"

    def normalize_axis(self, value):
        return int((value - 128) * 256)

    def apply_deadzone(self, value):
        if abs(value) < self.DEADZONE:
            return 0
        return value

    def _emit_mapped_key(self, mapped_name, value):
        try:
            mapped_code = getattr(ecodes, mapped_name)
            self.virtual.emit_key(mapped_code, value)
        except AttributeError:
            pass

    def _handle_hat_mapping(self, code, value):
        old_value = self.hat_state.get(code, 0)
        if old_value == value:
            return

        old_mapped = None
        if old_value in (-1, 1):
            old_mapped = self.mapper.translate(
                self.current_mode, code, old_value
            )
        if old_mapped:
            self._emit_mapped_key(old_mapped, 0)

        new_mapped = None
        if value in (-1, 1):
            new_mapped = self.mapper.translate(
                self.current_mode, code, value
            )
        if new_mapped:
            self._emit_mapped_key(new_mapped, 1)

        self.hat_state[code] = value

    def start(self):

        print("[+] Grabbing physical device...")
        self.physical.grab()
        print("[+] Forwarding events with dynamic mapping...")

        for event in self.physical.read_loop():

            # ------------------------
            # BUTTON EVENTS
            # ------------------------
            if event.type == ecodes.EV_KEY:

                mapped_name = self.mapper.translate(
                    self.current_mode,
                    event.code
                )

                if mapped_name:
                    self._emit_mapped_key(mapped_name, event.value)

            # ------------------------
            # AXIS EVENTS
            # ------------------------
            elif event.type == ecodes.EV_ABS:

                # Left Stick
                if event.code == ecodes.ABS_X:
                    value = self.apply_deadzone(
                        self.normalize_axis(event.value)
                    )
                    self.virtual.emit_abs(ecodes.ABS_X, value)

                elif event.code == ecodes.ABS_Y:
                    value = self.apply_deadzone(
                        self.normalize_axis(event.value)
                    )
                    self.virtual.emit_abs(ecodes.ABS_Y, value)

                # Right Stick (DragonRise)
                elif event.code == ecodes.ABS_Z:
                    value = self.apply_deadzone(
                        self.normalize_axis(event.value)
                    )
                    self.virtual.emit_abs(ecodes.ABS_RX, value)

                elif event.code == ecodes.ABS_RZ:
                    value = self.apply_deadzone(
                        self.normalize_axis(event.value)
                    )
                    self.virtual.emit_abs(ecodes.ABS_RY, value)

                # D-Pad
                elif event.code in (ecodes.ABS_HAT0X, ecodes.ABS_HAT0Y):
                    if self.mapper.has_axis_direction_mappings(
                        self.current_mode, event.code
                    ):
                        self._handle_hat_mapping(event.code, event.value)
                    else:
                        self.virtual.emit_abs(event.code, event.value)
