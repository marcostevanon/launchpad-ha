import unittest
from unittest.mock import MagicMock, patch

from ha_launchpad.config.mapping import RESTART_CHORD, RESTART_CHORD_TIMEOUT
from ha_launchpad.core.logic.input_handler import InputHandler


class TestInputHandlerRestart(unittest.TestCase):
    def setUp(self):
        self.ha_client = MagicMock()
        self.color_picker = MagicMock()
        self.color_picker.active = False
        self.disco = MagicMock()
        self.button_map = {15: "dummy1", 16: "dummy2"}
        self.handler = InputHandler(
            self.ha_client, self.button_map, self.color_picker, self.disco
        )

    def test_restart_chord_in_idle_mode(self):
        # 1. First button of chord
        res1 = self.handler.handle_press(RESTART_CHORD[0], is_idle=True)
        self.assertEqual(res1, {})
        self.assertEqual(self.handler._last_pressed_note, RESTART_CHORD[0])

        # 2. Second button of chord
        res2 = self.handler.handle_press(RESTART_CHORD[1], is_idle=True)
        self.assertEqual(res2, {"restart": True})

    def test_restart_chord_not_idle(self):
        # 1. First button
        res1 = self.handler.handle_press(RESTART_CHORD[0], is_idle=False)
        # Should be a toggle action
        self.assertIn("update_leds", res1)

        # 2. Second button
        res2 = self.handler.handle_press(RESTART_CHORD[1], is_idle=False)
        self.assertEqual(res2, {"restart": True})

    def test_restart_chord_expires_after_the_timeout(self):
        with patch("ha_launchpad.core.logic.input_handler.time.monotonic") as monotonic:
            monotonic.return_value = 0.0
            self.handler.handle_press(RESTART_CHORD[0], is_idle=True)

            # Second press arrives long after the first
            monotonic.return_value = RESTART_CHORD_TIMEOUT + 0.5
            res = self.handler.handle_press(RESTART_CHORD[1], is_idle=True)

        self.assertEqual(res, {})

    def test_restart_chord_within_the_timeout_still_fires(self):
        with patch("ha_launchpad.core.logic.input_handler.time.monotonic") as monotonic:
            monotonic.return_value = 0.0
            self.handler.handle_press(RESTART_CHORD[0], is_idle=True)

            monotonic.return_value = RESTART_CHORD_TIMEOUT - 0.1
            res = self.handler.handle_press(RESTART_CHORD[1], is_idle=True)

        self.assertEqual(res, {"restart": True})


if __name__ == "__main__":
    unittest.main()
