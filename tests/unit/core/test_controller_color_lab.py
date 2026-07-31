from unittest.mock import MagicMock

import pytest

from ha_launchpad.config.mapping import COLOR_LAB_BUTTON_CC, SCENE_COLUMN_CC
from ha_launchpad.core.controller import LaunchpadController


class ControlChange:
    """The shape mido hands over for a button around the grid."""

    type = "control_change"

    def __init__(self, control, value=127):
        self.control = control
        self.value = value


@pytest.fixture
def controller():
    return LaunchpadController(MagicMock(), {81: "light.test"}, backend=MagicMock())


def test_the_user_button_opens_and_closes_the_lab(controller):
    controller.handle_midi_message(ControlChange(COLOR_LAB_BUTTON_CC))
    assert controller.color_lab.active

    controller.handle_midi_message(ControlChange(COLOR_LAB_BUTTON_CC))
    assert not controller.color_lab.active


def test_releasing_a_button_is_not_a_second_press(controller):
    """The board sends 127 on press and 0 on release. Acting on both would
    open the lab and close it again before a finger left the button."""
    controller.handle_midi_message(ControlChange(COLOR_LAB_BUTTON_CC, value=127))
    controller.handle_midi_message(ControlChange(COLOR_LAB_BUTTON_CC, value=0))

    assert controller.color_lab.active


def test_the_buttons_around_the_grid_do_nothing_while_the_lab_is_closed(controller):
    controller.handle_midi_message(ControlChange(SCENE_COLUMN_CC[0]))

    assert not controller.color_lab.active
    controller.ha_client.toggle_entity.assert_not_called()


def test_a_swatch_press_never_reaches_home_assistant(controller):
    controller.color_lab.enter()

    controller._handle_note_on(81)
    controller._handle_note_off(81)

    controller.ha_client.toggle_entity.assert_not_called()
    controller.ha_client.call_service.assert_not_called()
    assert not controller.color_picker.active


def test_polling_leaves_the_palette_alone(controller):
    controller.led_manager = MagicMock()
    controller.color_lab.enter()

    controller.update_led_states()

    controller.led_manager.update_all.assert_not_called()


def test_closing_repaints_the_whole_board(controller):
    """The lab lights all 64 pads, including the ones no entity owns, so the
    LED manager alone would leave strays behind."""
    controller.led_manager = MagicMock()
    controller.led_manager.update_all.return_value = ([], False)
    controller.color_lab.enter()

    controller.handle_midi_message(ControlChange(COLOR_LAB_BUTTON_CC))

    controller.led_manager.invalidate_cache.assert_called()
    controller.led_manager.update_all.assert_called()


def test_opening_from_standby_wakes_the_board_first(controller):
    controller.idle_manager._is_idle = True

    controller.handle_midi_message(ControlChange(COLOR_LAB_BUTTON_CC))

    assert not controller.idle_manager.is_idle
    assert controller.color_lab.active
