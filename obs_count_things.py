import obspython as obs
from os.path import exists, dirname
import os


class TextContent:
    def __init__(self, counter_name="Default", source_name=None, text_string="This is default text"):
        self.counter_name = counter_name
        self.source_name = source_name
        self.text_string = text_string
        self.counter = 0
        
        obs.script_log(obs.LOG_INFO, f"Initializing TextContent with counter of {self.counter}")

    def set_counter(self, count):
        self.counter = count

    def update_text(self, counter_text, counter_value=0):
        source = obs.obs_get_source_by_name(self.source_name)
        settings = obs.obs_data_create()

        self.counter += counter_value
        if counter_value == 0:  # Reset case
            self.counter = 0

        self.text_string = f"{counter_text}{self.counter:,}"

        try:
            if exists(self.counter_save_path):
                with open(self.counter_save_path) as f:
                    counters = dict(line.strip().split(': ', 1) for line in f if ': ' in line)
            else:
                counters = {}
            
            counters[self.counter_name] = str(self.counter)
            
            with open(self.counter_save_path, 'w') as f:
                f.writelines(f"{name}: {value}\n" for name, value in counters.items())
                
        except Exception as e:
            print(f"Error saving counter: {e}")

        obs.obs_data_set_string(settings, "text", self.text_string)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)


class Driver(TextContent):
    def increment(self):
        self.update_text(self.counter_text, 1)

    def decrement(self):
        self.update_text(self.counter_text, -1)

    def reset(self):
        self.update_text(self.counter_text, 0)


class Hotkey:
    def __init__(self, callback, obs_settings, _id):
        self.obs_data = obs_settings
        self.hotkey_id = obs.OBS_INVALID_HOTKEY_ID
        self.hotkey_saved_key = None
        self.callback = callback
        self._id = _id

        self.load_hotkey()
        self.register_hotkey()
        self.save_hotkey()

    def register_hotkey(self):
        description = "OBS Count Things " + str(self._id)
        self.hotkey_id = obs.obs_hotkey_register_frontend(
            "htk_id" + str(self._id), description, self.callback
        )
        obs.obs_hotkey_load(self.hotkey_id, self.hotkey_saved_key)

    def load_hotkey(self):
        self.hotkey_saved_key = obs.obs_data_get_array(
            self.obs_data, "htk_id" + str(self._id)
        )
        obs.obs_data_array_release(self.hotkey_saved_key)

    def save_hotkey(self):
        self.hotkey_saved_key = obs.obs_hotkey_save(self.hotkey_id)
        obs.obs_data_set_array(
            self.obs_data, "htk_id" + str(self._id), self.hotkey_saved_key
        )
        obs.obs_data_array_release(self.hotkey_saved_key)


class HotkeyDataHolder:
    htk_copy = None  # this attribute will hold instance of Hotkey


hotkeys_counter = Driver()
h01 = HotkeyDataHolder()
h02 = HotkeyDataHolder()
h03 = HotkeyDataHolder()


def callback_up(pressed):
    if pressed:
        return hotkeys_counter.increment()


def callback_down(pressed):
    if pressed:
        return hotkeys_counter.decrement()


def callback_reset(pressed):
    if pressed:
        return hotkeys_counter.reset()

def get_available_counters(save_path):
    counters = []
    try:
        if exists(save_path):
            with open(save_path, "r") as f:
                for line in f:
                    if ':' in line:
                        counter_name = line.split(':')[0].strip()
                        if counter_name:
                            counters.append(counter_name)
    except Exception as e:
        print(f"Error reading counters from save file: {str(e)}")
    return counters


def script_description():
    return "We count things via OBS hotkey. See github.com/RetroTGaming/OBS-Count-Things for instructions"


def script_update(settings):
    hotkeys_counter.counter_name = obs.obs_data_get_string(settings, "counter_selection") or obs.obs_data_get_string(settings, "counter_name")
    hotkeys_counter.source_name = obs.obs_data_get_string(settings, "source")
    hotkeys_counter.counter_text = obs.obs_data_get_string(settings, "counter_text")
    save_path = obs.obs_data_get_string(settings, 'counter_save_path') or dirname(os.path.realpath(__file__))
    hotkeys_counter.counter_save_path = f"{save_path}\\obs_count_things_counter.txt"

    try:
        if not exists(hotkeys_counter.counter_save_path):
            with open(hotkeys_counter.counter_save_path, 'w') as f:
                f.write(f"{hotkeys_counter.counter_name}: 0")
            return

        with open(hotkeys_counter.counter_save_path) as f:
            counters = dict(line.strip().split(': ', 1) for line in f if ': ' in line)
            value = int(counters.get(hotkeys_counter.counter_name, 0))
            hotkeys_counter.set_counter(value)
            print(f"Loaded counter '{hotkeys_counter.counter_name}' with value {value}")

    except Exception as e:
        print(f"Error loading counter: {e}. Starting at 0")
        hotkeys_counter.set_counter(0)

def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_text(props, "counter_save_path", "Counter save directory", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "counter_text", "Text before counter", obs.OBS_TEXT_DEFAULT)

    p = obs.obs_properties_add_list(
        props, "counter_selection", "Select Counter",
        obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING
    )

    if hasattr(hotkeys_counter, 'counter_save_path') and exists(hotkeys_counter.counter_save_path):
        try:
            with open(hotkeys_counter.counter_save_path, "r") as f:
                counters = [line.split(':')[0].strip() for line in f if ':' in line]
                for counter in counters:
                    obs.obs_property_list_add_string(p, counter, counter)
        except Exception as e:
            print(f"Error loading counters: {e}")

    p1 = obs.obs_properties_add_list(
        props, "source", "Text Source",
        obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING
    )

    sources = obs.obs_enum_sources()
    if sources:
        for source in sources:
            if obs.obs_source_get_unversioned_id(source) in ["text_gdiplus", "text_ft2_source"]:
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p1, name, name)
        obs.source_list_release(sources)

    return props


def script_load(settings):
    h01.htk_copy = Hotkey(callback_up, settings, "count_up")
    h02.htk_copy = Hotkey(callback_down, settings, "count_down")
    h03.htk_copy = Hotkey(callback_reset, settings, "reset")

def script_save(settings):
    for h in [h01, h02, h03]:
        h.htk_copy.save_hotkey()
