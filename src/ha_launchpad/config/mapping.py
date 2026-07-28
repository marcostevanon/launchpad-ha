from typing import Any

# Launchpad button mapping (pad number -> HA entity)
BUTTON_MAP: dict[int, str] = {
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
    63: "switch.humidifier",
    # scenes
    85: "scene.i_m_home",
    86: "scene.i_m_leaving",
    87: "scene.bedtime",
    88: "scene.goodnight",
    75: "scene.living_room_bright",
    76: "scene.living_room_red",
    77: "scene.living_room_1",
    78: "disco_toggle",
    # media -- rows 6, 5 and 4, one device per row: play/pause, volume, volume.
    # Kept contiguous under the scenes so there is no gap in the middle of the
    # board; a row briefly held the living room TV and was removed, since the
    # only thing worth having from it was the power-off now on pad 58.
    65: "media_player.living_room_sonos",
    66: "volume_down.media_player.living_room_sonos",
    67: "volume_up.media_player.living_room_sonos",
    # Was media_player.nestmini7849, the Cast entity for this same Nest Mini.
    # This one keeps reporting `idle` rather than dropping to `off`, and it
    # supports next/previous track.
    55: "media_player.bathroom_speaker",
    56: "volume_down.media_player.bathroom_speaker",
    57: "volume_up.media_player.bathroom_speaker",
    # Powers the actual TV off, which no media_player entity here can do:
    # `media_player.living_room_tv` is the Chromecast, and the cast
    # integration's turn_off is only quit_app(). The script routes through
    # google_assistant_sdk so Google tells the dongle to emit an HDMI-CEC
    # standby -- the same path as saying it out loud. See docs/tv-power-off.md.
    58: "script.tv_off",
    45: "script.vinyl_play_on_sonos",
    46: "script.vinyl_stop",
    # plants
    17: "plant.monstera",
    18: "plant.pothos",
    # special
    68: "manual_sleep",
}

# Every addressable pad on the 8x8 grid.
#
# In Programmer Mode the Mini MK3 numbers pads `row * 10 + column`, with rows
# and columns running 1-8 from the bottom left. Iterating a raw `range(128)`
# instead sweeps in notes that are not pads at all, and rotating those produces
# negative note numbers the MIDI layer then rejects one by one.
ALL_PADS: tuple[int, ...] = tuple(
    row * 10 + col for row in range(1, 9) for col in range(1, 9)
)

# Special Buttons
IDLE_MODE_BUTTON_ID = 68
RESTART_CHORD = (15, 16)  # First button then second button
RESTART_CHORD_TIMEOUT = 2.0  # Seconds allowed between the two presses

# Pads that should enter color-pick mode when pressed (keys from BUTTON_MAP)
COLOR_PICK_ENABLED: set[int] = {81, 82, 83, 84, 62}

# Pads that should show brightness control (keys from BUTTON_MAP)
BRIGHTNESS_ENABLED: set[int] = {81, 82, 83, 84, 72, 61, 62}

# Mapping: pad -> brightness level (0.0 to 1.0)
# These will be shown on row 2 (21-28)
BRIGHTNESS_PALETTE: dict[int, float] = {
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
COLOR_PALETTE: dict[int, dict[str, Any]] = {
    41: {"color": "red_1", "rgb": (255, 0, 0)},
    42: {"color": "blue_1", "rgb": (105, 0, 255)},
    43: {"color": "yellow_3", "rgb": (255, 152, 57)},
    44: {"color": "green_1", "rgb": (0, 255, 0)},
    31: {"color": "orange_1", "rgb": (255, 97, 0)},
    32: {"color": "purple_1", "rgb": (239, 0, 255)},
    33: {"color": "yellow_1", "rgb": (255, 174, 92)},
    34: {"color": "white", "rgb": (255, 214, 161)},
}

COLORS: dict[str, int] = {
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
    # Out of sequence with the 8-15 orange block, but these are the velocities
    # `orange_2` and `orange_3` have always resolved to: the names were defined
    # twice and the later pair silently won.
    "orange_2": 60,
    "orange_3": 61,
    # extra
    "amber_1": 112,
}
