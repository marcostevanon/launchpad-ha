from unittest.mock import MagicMock

from ha_launchpad.core.controller import LaunchpadController


def test_press_on_a_sleeping_board_restores_the_pad_instead_of_blanking_it():
    controller = LaunchpadController(
        MagicMock(), {16: "binary_sensor.neighbour_home"}, backend=MagicMock()
    )
    controller.idle_manager.enter_idle()
    controller.idle_manager.restore_pad = MagicMock()

    controller.handle_button_press(16)

    controller.idle_manager.restore_pad.assert_called_once_with(16)
