from typing import Dict, Set, Any

# Launchpad button mapping (pad number -> HA entity)
BUTTON_MAP: Dict[int, str] = {
    # living room
    81: "light.living_room_spotlights",
    82: "light.bulb_1",
    83: "light.bulb_2",
    84: "light.bulb_3",
    71: "switch.living_room_bulbs_string",
    72: "light.living_room_lamp",
    73: "switch.living_room_neon",

    # bedroom
    61: "light.bulb_bedroom",
    62: "light.bedroom_lamp",

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
    17: "plant.monstera",
    18: "plant.pothos",
}

# Special Buttons
SLEEP_BUTTON_ID = 68
WAKE_BUTTON_ID = 91 # Top-Left usually

# Pads that should enter color-pick mode when pressed (keys from BUTTON_MAP)
COLOR_PICK_ENABLED: Set[int] = {81, 82, 83, 84, 62}

# Pads that should show brightness control (keys from BUTTON_MAP)
BRIGHTNESS_ENABLED: Set[int] = {81, 82, 83, 84, 72, 61, 62}

# Mapping: pad -> brightness level (0.0 to 1.0)
# These will be shown on row 2 (21-28)
BRIGHTNESS_PALETTE: Dict[int, float] = {
    21: 0.1,
    22: 0.25,
    23: 0.4,
    24: 0.55,
    11: 0.7,
    12: 0.85,
    13: 0.95,
    14: 1.0,
}

# Palette display mapping: map pad -> color name in `COLORS` for non-RGB devices.
# Use these for lighting pads when RGB SysEx isn't available.
COLOR_PALETTE: Dict[int, Dict[str, Any]] = {
    41: {"color": "red_1", "rgb": (255, 0, 0)},
    42: {"color": "blue_1", "rgb": (105, 0, 255)},
    43: {"color": "yellow_3", "rgb": (255, 152, 57)},
    44: {"color": "green_1", "rgb": (0, 255, 0)},
    31: {"color": "orange_1", "rgb": (255, 97, 0)},
    32: {"color": "purple_1", "rgb": (239, 0, 255)},
    33: {"color": "yellow_1", "rgb": (255, 174, 92)},
    34: {"color": "white", "rgb": (255, 214, 161)},
}

COLORS: Dict[str, int] = {
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
