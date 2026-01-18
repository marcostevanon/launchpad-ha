import py
import pytest
from unittest.mock import MagicMock, patch
import time
from src.ha_launchpad.core.logic.idle_manager import IdleManager
from src.ha_launchpad.config.mapping import WAKE_BUTTON_ID

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
        from src.ha_launchpad.config.settings import IDLE_TIMEOUT
        mock_time.return_value = IDLE_TIMEOUT + 10
        
        idle_manager.check_status()
        assert idle_manager.is_idle

def test_wake_up(idle_manager):
    idle_manager.set_manual_sleep()
    assert idle_manager.is_idle
    
    idle_manager.wake_up()
    assert not idle_manager.is_idle

def test_notification_visuals(idle_manager):
    idle_manager.backend.is_connected.return_value = True
    
    # Enter sleep - No notification -> Green
    idle_manager.enter_idle()
    idle_manager.backend.send_note.assert_any_call(WAKE_BUTTON_ID, "green_2")
    
    # Set notification -> Orange
    idle_manager.set_notification_status(True)
    idle_manager.backend.send_note.assert_any_call(WAKE_BUTTON_ID, "orange_1")
    
    # Clear notification -> Green
    idle_manager.set_notification_status(False)
    idle_manager.backend.send_note.assert_any_call(WAKE_BUTTON_ID, "green_2")
