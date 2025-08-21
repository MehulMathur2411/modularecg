import json
import os

class SettingsManager:
    def __init__(self):
        self.settings_file = "ecg_settings.json"
        self.default_settings = {
            "wave_speed": "50",  # mm/s
            "wave_gain": "10",   # mm/mV
            "lead_sequence": "Standard",
            "sampling_mode": "Simultaneous",
            "demo_function": "Off",
            "storage": "SD",
            "serial_port": "Select Port",
            "baud_rate": "115200"
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    
                    merged_settings = self.default_settings.copy()
                    merged_settings.update(loaded_settings)
                    return merged_settings
            except:
                return self.default_settings.copy()
        return self.default_settings.copy()
    
    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def get_setting(self, key):
        return self.settings.get(key, self.default_settings.get(key))
    
    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()
        print(f"Setting updated: {key} = {value}")  # Terminal verification
    
    def get_wave_speed(self):
        return float(self.get_setting("wave_speed"))
    
    def get_wave_gain(self):
        return float(self.get_setting("wave_gain"))

    def get_serial_port(self):
        return self.get_setting("serial_port")
    
    def get_baud_rate(self):
        return self.get_setting("baud_rate")
