from unittest.mock import MagicMock, patch

import pytest

from ha_launchpad.config.mapping import IDLE_MODE_BUTTON_ID
from ha_launchpad.core.logic.idle_manager import IdleManager


@pytest.fixture
def idle_manager():
    backend = MagicMock()
    # Mock settings.IDLE_TIMEOUT if possible, or just rely on patching time
    return IdleManager(backend)

def test_initial_state(idle_manager):
    assert not idle_manager.is_idle

def test_manual_sleep(idle_manager):
    idle_manager.set_manual_sleep()
    assert idle_manager.is_idle
    # Should have cleared LEDs
    assert idle_manager.backend.send_note.call_count >= 1

def test_activity_updates_timestamp(idle_manager):
    with patch('time.time') as mock_time:
        mock_time.return_value = 1000
        idle_manager.register_activity()
        assert idle_manager._last_activity_time == 1000

def test_timeout_triggers_idle(idle_manager):
    with patch('time.time') as mock_time:
        # Start at 0
        mock_time.return_value = 0
        idle_manager._last_activity_time = 0
        
        # Advance time past threshold (assuming default 1800)
        from ha_launchpad.config.settings import IDLE_TIMEOUT
        mock_time.return_value = IDLE_TIMEOUT + 10
        
        idle_manager.check_status()
        assert idle_manager.is_idle

def test_wake_up_resets_the_inactivity_timer(idle_manager):
    """Waking must restart the clock. It used to leave `_last_activity_time`
    at its old value, so the next status check saw an elapsed time still over
    the threshold and put the board straight back to sleep."""
    from ha_launchpad.config.settings import IDLE_TIMEOUT

    with patch('time.time') as mock_time:
        mock_time.return_value = 0
        idle_manager._last_activity_time = 0

        mock_time.return_value = IDLE_TIMEOUT + 10
        idle_manager.check_status()
        assert idle_manager.is_idle

        idle_manager.wake_up()
        assert not idle_manager.is_idle

        # Without a timer reset this check re-enters sleep immediately.
        idle_manager.check_status()
        assert not idle_manager.is_idle


def test_wake_up(idle_manager):
    idle_manager.set_manual_sleep()
    assert idle_manager.is_idle
    
    idle_manager.wake_up()
    assert not idle_manager.is_idle

def test_standby_preview_lights_changed_pads_without_waking(idle_manager):
    idle_manager.backend.is_connected.return_value = True
    idle_manager.enter_idle()
    idle_manager.backend.send_note.reset_mock()

    idle_manager.show_standby_preview([(81, "green_1", 0)])

    idle_manager.backend.send_note.assert_called_once_with(81, "green_1", 0)
    assert idle_manager.is_idle


def test_standby_preview_turns_itself_off_when_it_expires(idle_manager):
    from ha_launchpad.config.settings import STANDBY_PREVIEW_DURATION

    idle_manager.backend.is_connected.return_value = True

    with patch('time.time') as mock_time:
        mock_time.return_value = 0
        idle_manager.show_standby_preview([(81, "green_1", 0)])

        # Still within the window: leave it lit.
        mock_time.return_value = STANDBY_PREVIEW_DURATION - 1
        idle_manager.backend.send_note.reset_mock()
        idle_manager.expire_standby_preview()
        idle_manager.backend.send_note.assert_not_called()

        # Past the window: turn it back off.
        mock_time.return_value = STANDBY_PREVIEW_DURATION + 1
        idle_manager.expire_standby_preview()
        idle_manager.backend.send_note.assert_called_once_with(81, "off")


def test_standby_preview_leaves_the_wake_button_alone(idle_manager):
    idle_manager.backend.is_connected.return_value = True

    idle_manager.show_standby_preview([(IDLE_MODE_BUTTON_ID, "green_1", 0)])

    idle_manager.backend.send_note.assert_not_called()


def test_notification_visuals(idle_manager):
    idle_manager.backend.is_connected.return_value = True
    
    # Enter sleep - No notification -> Lightblue
    idle_manager.enter_idle()
    idle_manager.backend.send_note.assert_any_call(IDLE_MODE_BUTTON_ID, "lightblue_0")
    
    # Set notification -> Orange
    idle_manager.set_notification_status(True)
    idle_manager.backend.send_note.assert_any_call(IDLE_MODE_BUTTON_ID, "orange_1")
    
    # Clear notification -> Lightblue
    idle_manager.set_notification_status(False)
    idle_manager.backend.send_note.assert_any_call(IDLE_MODE_BUTTON_ID, "lightblue_0")
