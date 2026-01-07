from typing import Dict
import os

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/ha-launchpad.out.log")

HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))

LAUNCHPAD_VENDOR = int(os.getenv("LAUNCHPAD_VENDOR", "0x1235"), 16)
LAUNCHPAD_PRODUCT = int(os.getenv("LAUNCHPAD_PRODUCT", "0x0113"), 16)
LAUNCHPAD_IDENT = os.getenv("LAUNCHPAD_IDENT", "LPMiniMK3 MIDI")
LAUNCHPAD_INACTIVITY_TIMEOUT = float(os.getenv("LAUNCHPAD_INACTIVITY_TIMEOUT", "15.0"))

HA_CONNECT_RETRY_DELAY = float(os.getenv("HA_CONNECT_RETRY_DELAY", "3.0"))
HA_CONNECT_MAX_DELAY = float(os.getenv("HA_CONNECT_MAX_DELAY", "30.0"))
HA_REQUEST_RETRY_DELAY = float(os.getenv("HA_REQUEST_RETRY_DELAY", "2.0"))
HA_REQUEST_MAX_DELAY = float(os.getenv("HA_REQUEST_MAX_DELAY", "5.0"))

VOLUME_STEP = float(os.getenv("VOLUME_STEP", "0.1"))

LAUNCHPAD_ALIVE_DELAY = float(os.getenv("LAUNCHPAD_ALIVE_DELAY", "3.0"))
LAUNCHPAD_RETRY_DELAY = float(os.getenv("LAUNCHPAD_RETRY_DELAY", "5.0"))
LAUNCHPAD_MAX_RETRY_DELAY = float(os.getenv("LAUNCHPAD_MAX_RETRY_DELAY", "10.0"))

LAUNCHPAD_ROTATION = int(os.getenv("LAUNCHPAD_ROTATION", "180"))

if LAUNCHPAD_ROTATION not in {0, 90, 180, 270}:
    raise ValueError("LAUNCHPAD_ROTATION must be 0, 90, 180 or 270")

DISCO_LIGHTS = ["light.bulb_1", "light.bulb_2", "light.bulb_3"]
DISCO_SPEED = float(os.getenv("DISCO_SPEED", "0.5"))

# Launchpad button mapping (pad number -> HA entity)
BUTTON_MAP: Dict[int, str] = {
    # living room
    81: "light.living_room_spotlights",
    82: "switch.living_room_bulbs_string",
    83: "light.living_room_lamp",
    84: "switch.living_room_neon",
    71: "light.bulb_1",
    61: "light.bulb_2",
    51: "light.bulb_3",

    # bedroom
    64: "light.bulb_bedroom",
    54: "light.bedroom_lamp",

    # scenes
    85: "scene.i_m_home",
    86: "scene.i_m_leaving",
    87: "scene.bedtime",
    88: "scene.goodnight",
    75: "scene.living_room_bright",
    76: "scene.living_room_red",
    77: "scene.living_room_1",
    78: "disco_toggle",

    # media
    65: "media_player.living_room_sonos",
    66: "volume_down.media_player.living_room_sonos",
    67: "volume_up.media_player.living_room_sonos",

    55: "media_player.studio_speaker",
    56: "volume_down.media_player.studio_speaker",
    57: "volume_up.media_player.studio_speaker",

    45: "media_player.nestmini7849",
    46: "volume_down.media_player.nestmini7849",
    47: "volume_up.media_player.nestmini7849",

    # plants
    11: "plant.monstera",
    12: "plant.pothos",
}

# Pads that should enter color-pick mode when pressed (keys from BUTTON_MAP)
COLOR_PICK_ENABLED = {54, 81, 71, 61, 51}

# Palette display mapping: map pad -> color name in `COLORS` for non-RGB devices.
# Use these for lighting pads when RGB SysEx isn't available.
COLOR_PALETTE = {
    41: {"color": "red_1", "rgb": (255, 0, 0)},
    42: {"color": "blue_1", "rgb": (105, 0, 255)},
    43: {"color": "yellow_3", "rgb": (255, 152, 57)},
    44: {"color": "green_1", "rgb": (0, 255, 0)},
    31: {"color": "orange_1", "rgb": (255, 97, 0)},
    32: {"color": "purple_1", "rgb": (239, 0, 255)},
    33: {"color": "yellow_1", "rgb": (255, 174, 92)},
    34: {"color": "white", "rgb": (255, 214, 161)},
}

COLORS = {
    # 0–7
    "off": 0,
    "gray_1": 1,
    "gray_2": 2,
    "white": 3,
    "red_0": 4,
    "red_1": 5,
    "red_2": 6,
    "red_3": 7,
    # 8–15
    "orange_0": 8,
    "orange_1": 9,
    "orange_2": 10,
    "orange_3": 11,
    "yellow_0": 12,
    "yellow_1": 13,
    "yellow_2": 14,
    "yellow_3": 15,
    # 16–23
    "green_0": 20,
    "green_1": 21,
    "green_2": 22,
    "green_3": 23,
    # 32–39
    "cyan_0": 36,
    "cyan_1": 37,
    "cyan_2": 38,
    "cyan_3": 39,
    # 40–47
    "lightblue_0": 40,
    "lightblue_1": 41,
    "lightblue_2": 42,
    "lightblue_3": 43,
    "blue_0": 44,
    "blue_1": 45,
    "blue_2": 46,
    "blue_3": 47,
    # 48–55
    "purple_0": 48,
    "purple_1": 49,
    "purple_2": 50,
    "purple_3": 51,
    # 56–63
    "pink_1": 56,
    "pink_2": 57,
    "pink_3": 58,
    "pink_4": 59,
    "orange_2": 60,
    "orange_3": 61,
    # extra
    "amber_1": 112,
}
