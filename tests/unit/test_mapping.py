import ast
from pathlib import Path

from ha_launchpad.config import mapping as mapping_module
from ha_launchpad.config.mapping import (
    BUTTON_MAP,
    COLOR_PALETTE,
    COLOR_PICK_ENABLED,
    COLORS,
)


def test_button_map_keys_are_integers():
    for key in BUTTON_MAP:
        assert isinstance(key, int)

def test_button_map_values_are_strings():
    for value in BUTTON_MAP.values():
        assert isinstance(value, str)

def test_color_pick_enabled_are_in_map():
    # All color pick enabled buttons should be mapped functionality
    for note in COLOR_PICK_ENABLED:
        assert note in BUTTON_MAP

def test_no_duplicate_keys_in_mapping_tables():
    """A repeated key is silently dropped when the dict literal is evaluated,
    so the only way to catch it is to read the source."""
    tree = ast.parse(Path(mapping_module.__file__).read_text())

    duplicates = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        if not isinstance(node.value, ast.Dict):
            continue

        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
        name = getattr(target, "id", None)
        if name is None:
            continue

        keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
        repeated = sorted({k for k in keys if keys.count(k) > 1})
        if repeated:
            duplicates[name] = repeated

    assert not duplicates, f"later entries silently shadow earlier ones: {duplicates}"


def test_palette_colors_exist():
    # All colors in palette should exist in COLORS
    for info in COLOR_PALETTE.values():
        color_name = info["color"]
        assert color_name in COLORS or color_name == "off"

