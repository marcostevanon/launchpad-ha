from unittest.mock import MagicMock

import pytest

from ha_launchpad.config.mapping import RESTART_CHORD
from ha_launchpad.core.logic.input_handler import InputHandler


def _handler(button_map):
    color_picker = MagicMock()
    color_picker.active = False
    return InputHandler(MagicMock(), button_map, color_picker, MagicMock())


@pytest.mark.parametrize(
    "entity_id", ["binary_sensor.neighbour_home", "plant.monstera"]
)
def test_read_only_pad_calls_nothing(entity_id):
    handler = _handler({16: entity_id})

    assert handler.handle_press(16) == {}
    handler.ha_client.toggle_entity.assert_not_called()


def test_light_pad_still_toggles():
    handler = _handler({81: "light.a"})
    handler.ha_client.toggle_entity.return_value = True

    handler.handle_press(81)

    handler.ha_client.toggle_entity.assert_called_once_with("light.a")


def test_restart_chord_still_fires_when_its_second_pad_is_a_status_pad():
    handler = _handler({RESTART_CHORD[1]: "binary_sensor.neighbour_home"})

    handler.handle_press(RESTART_CHORD[0])

    assert handler.handle_press(RESTART_CHORD[1]) == {"restart": True}
