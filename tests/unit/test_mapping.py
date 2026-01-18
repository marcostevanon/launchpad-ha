from src.ha_launchpad.config.mapping import BUTTON_MAP, COLOR_PICK_ENABLED, COLORS, COLOR_PALETTE

def test_button_map_keys_are_integers():
    for key in BUTTON_MAP.keys():
        assert isinstance(key, int)

def test_button_map_values_are_strings():
    for value in BUTTON_MAP.values():
        assert isinstance(value, str)

def test_color_pick_enabled_are_in_map():
    # All color pick enabled buttons should be mapped functionality
    for note in COLOR_PICK_ENABLED:
        assert note in BUTTON_MAP

def test_palette_colors_exist():
    # All colors in palette should exist in COLORS
    for info in COLOR_PALETTE.values():
        color_name = info["color"]
        assert color_name in COLORS or color_name == "off"

