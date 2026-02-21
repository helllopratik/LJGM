import json
import os

CONFIG_PATH = "config/profile.json"


class Mapper:

    def __init__(self):
        self.data = {}
        self.load()

    def load(self):

        if not os.path.exists(CONFIG_PATH):
            self._create_default()
            return

        try:
            with open(CONFIG_PATH, "r") as f:
                content = f.read().strip()

                if not content:
                    self._create_default()
                    return

                loaded = json.loads(content)

                # ---------- AUTO MIGRATION ----------
                # If old format detected
                if "buttons" in loaded and "analog" not in loaded:
                    self.data = {
                        "analog": {"buttons": loaded.get("buttons", {})},
                        "digital": {"buttons": {}}
                    }
                    self.save()
                    return

                # Ensure required keys exist
                if "analog" not in loaded:
                    loaded["analog"] = {"buttons": {}}
                if "digital" not in loaded:
                    loaded["digital"] = {"buttons": {}}
                if "buttons" not in loaded["analog"]:
                    loaded["analog"]["buttons"] = {}
                if "buttons" not in loaded["digital"]:
                    loaded["digital"]["buttons"] = {}

                self.data = loaded

        except Exception:
            self._create_default()

    def _create_default(self):
        self.data = {
            "analog": {"buttons": {}},
            "digital": {"buttons": {}}
        }
        self.save()

    def save(self):
        os.makedirs("config", exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.data, f, indent=4)

    def set_mapping(self, mode, physical_code, virtual_button):
        self.data[mode]["buttons"][str(physical_code)] = virtual_button
        self.save()

    def translate(self, mode, physical_code):
        return self.data.get(mode, {}).get("buttons", {}).get(str(physical_code))

    def is_empty(self):
        return (
            not self.data.get("analog", {}).get("buttons") and
            not self.data.get("digital", {}).get("buttons")
        )
