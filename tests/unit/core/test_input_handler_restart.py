import unittest
from unittest.mock import MagicMock
from src.ha_launchpad.core.logic.input_handler import InputHandler
from src.ha_launchpad.config.mapping import RESTART_CHORD

class TestInputHandlerRestart(unittest.TestCase):
    def setUp(self):
        self.ha_client = MagicMock()
        self.color_picker = MagicMock()
        self.color_picker.active = False
        self.disco = MagicMock()
        self.button_map = {15: "dummy1", 16: "dummy2"}
        self.handler = InputHandler(
            self.ha_client,
            self.button_map,
            self.color_picker,
            self.disco
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

if __name__ == "__main__":
    unittest.main()
