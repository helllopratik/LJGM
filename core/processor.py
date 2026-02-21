from evdev import ecodes


class InputProcessor:

    def __init__(self, device, virtual):

        self.device = device
        self.virtual = virtual

        from core.mapper import Mapper
        self.mapper = Mapper()

        self.current_mode = "analog"

    def start(self):

        print("[+] Grabbing physical device...")
        self.device.grab()

        print("[+] Forwarding events with dynamic mapping...")

        for event in self.device.read_loop():

            # BUTTON EVENTS
            if event.type == ecodes.EV_KEY:

                mode_data = self.mapper.data.get(self.current_mode, {})
                button_map = mode_data.get("buttons", {})

                mapped_name = button_map.get(str(event.code))

                if mapped_name:
                    # Convert string name like "BTN_A" to ecodes value
                    mapped_code = getattr(ecodes, mapped_name)
                    self.virtual.emit_button(mapped_code, event.value)

            # AXIS EVENTS
            elif event.type == ecodes.EV_ABS:

                mode_data = self.mapper.data.get(self.current_mode, {})
                axis_map = mode_data.get("axes", {})

                mapped_name = axis_map.get(str(event.code))

                if mapped_name:
                    mapped_code = getattr(ecodes, mapped_name)
                    self.virtual.emit_axis(mapped_code, event.value)