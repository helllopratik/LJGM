import json
import os

CONFIG_PATH = "config/profile.json"


DEFAULT_STRUCTURE = {
    "analog": {
        "buttons": {},
        "axes": {}
    },
    "digital": {
        "buttons": {},
        "axes": {}
    }
}


class Mapper:

    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if not os.path.exists(CONFIG_PATH):
            self.data = DEFAULT_STRUCTURE.copy()
            self.save()
            return

        try:
            with open(CONFIG_PATH, "r") as f:
                self.data = json.load(f)
        except:
            self.data = DEFAULT_STRUCTURE.copy()
            self.save()

        # Ensure keys exist
        for mode in ["analog", "digital"]:
            if mode not in self.data:
                self.data[mode] = {"buttons": {}, "axes": {}}

    def save(self):
        os.makedirs("config", exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.data, f, indent=4)

    def set_button(self, mode, physical_code, virtual_code):
        self.data[mode]["buttons"][str(physical_code)] = virtual_code
        self.save()

    def set_axis(self, mode, physical_code, virtual_code):
        self.data[mode]["axes"][str(physical_code)] = virtual_code
        self.save()

    def translate_button(self, mode, physical_code):
        return self.data.get(mode, {}).get("buttons", {}).get(str(physical_code))

    def translate_axis(self, mode, physical_code):
        return self.data.get(mode, {}).get("axes", {}).get(str(physical_code))

    def is_empty(self):
        for mode in ["analog", "digital"]:
            if self.data[mode]["buttons"] or self.data[mode]["axes"]:
                return False
        return True