import pytest
from unittest.mock import MagicMock

from src.ha_launchpad.core.logic.led_manager import LEDManager


@pytest.fixture
def led_manager():
    disco = MagicMock()
    disco.active = False
    return LEDManager(MagicMock(), MagicMock(), {81: "light.a"}, disco)


def _states(state):
    return [{"entity_id": "light.a", "state": state, "attributes": {"brightness": 255}}]


def test_dry_run_reports_the_change_without_emitting(led_manager):
    led_manager.ha_client.get_all_states.return_value = _states("on")

    changed, _ = led_manager.update_all(dry_run=True)

    assert changed
    led_manager.backend.send_note.assert_not_called()


def test_dry_run_does_not_consume_the_change(led_manager):
    """A dry run must not bank the new state as though it had been painted.

    While the board is asleep every poll is a dry run. If those runs updated
    the cache, the repaint on wake would find nothing to send and the board
    would come back blank -- lighting up only pads that happened to change
    afterwards.
    """
    led_manager.ha_client.get_all_states.return_value = _states("on")

    led_manager.update_all(dry_run=True)
    changed, _ = led_manager.update_all(dry_run=False)

    assert changed
    led_manager.backend.send_note.assert_called_once_with(81, "green_1", 0)


def test_unchanged_state_is_not_resent(led_manager):
    led_manager.ha_client.get_all_states.return_value = _states("on")

    led_manager.update_all(dry_run=False)
    led_manager.backend.send_note.reset_mock()
    changed, _ = led_manager.update_all(dry_run=False)

    assert not changed
    led_manager.backend.send_note.assert_not_called()


def test_failed_fetch_leaves_the_board_alone(led_manager):
    led_manager.ha_client.get_all_states.return_value = []

    changed, has_notifications = led_manager.update_all(dry_run=False)

    assert not changed
    assert not has_notifications
    led_manager.backend.send_note.assert_not_called()
