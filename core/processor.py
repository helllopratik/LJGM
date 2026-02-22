import os
import time
import errno
from evdev import ecodes, UInput
from core.mapper import Mapper


class InputProcessor:

    DEADZONE = 4000

    def __init__(self, physical, virtual):
        self.physical = physical
        self.virtual = virtual
        self.mapper = Mapper()
        self.use_mouse_mode = False
        self.mouse_ui = None
        self.stick_sensitivity = 1.0
        self.mouse_sensitivity = 1.0
        self.axis_info = dict(physical.capabilities(absinfo=True).get(ecodes.EV_ABS, []))
        self.hat_state = {
            ecodes.ABS_HAT0X: 0,
            ecodes.ABS_HAT0Y: 0,
        }
        self.key_dpad_state = {
            "BTN_DPAD_LEFT": 0,
            "BTN_DPAD_RIGHT": 0,
            "BTN_DPAD_UP": 0,
            "BTN_DPAD_DOWN": 0,
        }
        self.running = False
        self.cleaned_up = False

        # For now default mode = analog
        # Later we will auto-detect LED state
        self.current_mode = "analog"

    def normalize_axis(self, axis_code, value):
        info = self.axis_info.get(axis_code)
        if info and info.max > info.min:
            center = (info.min + info.max) / 2.0
            span = max(center - info.min, info.max - center)
            if span > 0:
                normalized = int(((value - center) / span) * 32767)
                return max(-32768, min(32767, normalized))

        # Fallback for unknown axis metadata.
        return int((value - 128) * 256)

    def apply_deadzone(self, value):
        if abs(value) < self.DEADZONE:
            return 0
        return value

    def _apply_stick_sensitivity(self, value):
        scaled = int(value * self.stick_sensitivity)
        return max(-32768, min(32767, scaled))

    def _emit_mapped_key(self, mapped_name, value):
        if mapped_name in self.key_dpad_state:
            self.key_dpad_state[mapped_name] = 1 if value else 0
            hat_x = self.key_dpad_state["BTN_DPAD_RIGHT"] - self.key_dpad_state["BTN_DPAD_LEFT"]
            hat_y = self.key_dpad_state["BTN_DPAD_DOWN"] - self.key_dpad_state["BTN_DPAD_UP"]
            self.virtual.emit_abs(ecodes.ABS_HAT0X, hat_x)
            self.virtual.emit_abs(ecodes.ABS_HAT0Y, hat_y)
            return
        try:
            mapped_code = getattr(ecodes, mapped_name)
            self.virtual.emit_key(mapped_code, value)
        except AttributeError:
            pass

    def _setup_mouse(self):
        if self.mouse_ui:
            return
        self.mouse_ui = UInput(
            {
                ecodes.EV_KEY: [
                    ecodes.BTN_MOUSE,
                    ecodes.BTN_LEFT,
                    ecodes.BTN_RIGHT,
                    ecodes.BTN_MIDDLE,
                ],
                ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL],
            },
            name="LJGM Virtual Mouse",
            bustype=ecodes.BUS_USB
        )

    def set_mouse_mode(self, enabled):
        self.use_mouse_mode = enabled
        if enabled:
            self._setup_mouse()

    def set_stick_sensitivity(self, percent):
        self.stick_sensitivity = max(0.1, min(5.0, percent / 100.0))

    def set_mouse_sensitivity(self, percent):
        self.mouse_sensitivity = max(0.1, min(6.0, percent / 100.0))

    def _axis_to_mouse_delta(self, value):
        magnitude = abs(value)
        if magnitude < 3000:
            return 0
        # Blend base speed with configurable sensitivity.
        delta = max(1, int((magnitude / 2200.0) * self.mouse_sensitivity))
        delta = min(40, delta)
        return -delta if value < 0 else delta

    def _emit_mouse_move(self, axis_code, value):
        if not self.mouse_ui:
            return

        delta = self._axis_to_mouse_delta(value)
        if delta == 0:
            return

        rel_code = ecodes.REL_X if axis_code == ecodes.ABS_X else ecodes.REL_Y
        self.mouse_ui.write(ecodes.EV_REL, rel_code, delta)
        self.mouse_ui.syn()

    def _emit_mouse_from_hat(self, axis_code, axis_value):
        if not self.mouse_ui or axis_value == 0:
            return

        step = max(1, int(6 * self.mouse_sensitivity))
        delta = step if axis_value > 0 else -step
        rel_code = ecodes.REL_X if axis_code == ecodes.ABS_HAT0X else ecodes.REL_Y
        self.mouse_ui.write(ecodes.EV_REL, rel_code, delta)
        self.mouse_ui.syn()

    def _handle_mouse_bound_button(self, mapped_name, value):
        if not self.mouse_ui:
            return False

        if mapped_name == "BTN_A":
            self.mouse_ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, value)
            self.mouse_ui.syn()
            return True

        if mapped_name == "BTN_B":
            self.mouse_ui.write(ecodes.EV_KEY, ecodes.BTN_RIGHT, value)
            self.mouse_ui.syn()
            return True

        if mapped_name == "BTN_Y":
            self.mouse_ui.write(ecodes.EV_KEY, ecodes.BTN_MIDDLE, value)
            self.mouse_ui.syn()
            return True

        if mapped_name == "BTN_X" and value == 1:
            for _ in range(2):
                self.mouse_ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
                self.mouse_ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
            self.mouse_ui.syn()
            return True

        if mapped_name == "BTN_TL" and value == 1:
            self.mouse_ui.write(ecodes.EV_REL, ecodes.REL_WHEEL, 1)
            self.mouse_ui.syn()
            return True

        if mapped_name == "BTN_TR" and value == 1:
            self.mouse_ui.write(ecodes.EV_REL, ecodes.REL_WHEEL, -1)
            self.mouse_ui.syn()
            return True

        return False

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

    def stop(self):
        self.running = False
        try:
            self.physical.ungrab()
        except Exception:
            pass

    def cleanup(self):
        if self.cleaned_up:
            return
        self.cleaned_up = True

        try:
            self.physical.ungrab()
        except Exception:
            pass
        try:
            self.physical.close()
        except Exception:
            pass
        if self.mouse_ui:
            try:
                self.mouse_ui.close()
            except Exception:
                pass
            self.mouse_ui = None
        if self.virtual:
            try:
                self.virtual.close()
            except Exception:
                pass

    def start(self):

        if self.use_mouse_mode:
            self._setup_mouse()

        print("[+] Grabbing physical device...")
        grabbed = False
        for _ in range(100):
            try:
                self.physical.grab()
                grabbed = True
                break
            except OSError as e:
                # Device may be temporarily busy while previous session releases.
                if e.errno in (errno.EBUSY, errno.EAGAIN):
                    time.sleep(0.05)
                    continue
                raise
        if not grabbed:
            raise OSError(errno.EBUSY, "Failed to grab input device after retries")

        os.set_blocking(self.physical.fd, False)
        print("[+] Forwarding events with dynamic mapping...")
        self.running = True

        try:
            while self.running:
                try:
                    event = self.physical.read_one()
                except BlockingIOError:
                    time.sleep(0.005)
                    continue
                except OSError as e:
                    # Non-blocking reads can also surface EAGAIN as plain OSError.
                    if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                        time.sleep(0.005)
                        continue
                    break

                if event is None:
                    time.sleep(0.005)
                    continue

                # ------------------------
                # BUTTON EVENTS
                # ------------------------
                if event.type == ecodes.EV_KEY:

                    mapped_name = self.mapper.translate(
                        self.current_mode,
                        event.code
                    )

                    if mapped_name:
                        if self.use_mouse_mode and self._handle_mouse_bound_button(
                            mapped_name, event.value
                        ):
                            continue
                        self._emit_mapped_key(mapped_name, event.value)

                # ------------------------
                # AXIS EVENTS
                # ------------------------
                elif event.type == ecodes.EV_ABS:

                    # Left Stick
                    if event.code == ecodes.ABS_X:
                        value = self.apply_deadzone(
                            self.normalize_axis(event.code, event.value)
                        )
                        value = self._apply_stick_sensitivity(value)
                        if self.use_mouse_mode:
                            self._emit_mouse_move(event.code, value)
                        else:
                            self.virtual.emit_abs(ecodes.ABS_X, value)

                    elif event.code == ecodes.ABS_Y:
                        value = self.apply_deadzone(
                            self.normalize_axis(event.code, event.value)
                        )
                        value = self._apply_stick_sensitivity(value)
                        if self.use_mouse_mode:
                            self._emit_mouse_move(event.code, value)
                        else:
                            self.virtual.emit_abs(ecodes.ABS_Y, value)

                    # Right Stick (DragonRise)
                    elif event.code == ecodes.ABS_Z:
                        value = self.apply_deadzone(
                            self.normalize_axis(event.code, event.value)
                        )
                        value = self._apply_stick_sensitivity(value)
                        self.virtual.emit_abs(ecodes.ABS_RX, value)

                    elif event.code == ecodes.ABS_RZ:
                        value = self.apply_deadzone(
                            self.normalize_axis(event.code, event.value)
                        )
                        value = self._apply_stick_sensitivity(value)
                        self.virtual.emit_abs(ecodes.ABS_RY, value)

                    # D-Pad
                    elif event.code in (ecodes.ABS_HAT0X, ecodes.ABS_HAT0Y):
                        if self.use_mouse_mode and self.current_mode == "digital":
                            self._emit_mouse_from_hat(event.code, event.value)
                            continue
                        if self.mapper.has_axis_direction_mappings(
                            self.current_mode, event.code
                        ):
                            self._handle_hat_mapping(event.code, event.value)
                        else:
                            self.virtual.emit_abs(event.code, event.value)
        finally:
            self.cleanup()
