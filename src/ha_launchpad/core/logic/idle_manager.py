import time
import logging
from typing import Optional

from src.ha_launchpad.config.settings import IDLE_TIMEOUT
from src.ha_launchpad.config.mapping import WAKE_BUTTON_ID, SLEEP_BUTTON_ID
from src.ha_launchpad.infrastructure.midi.interface import MidiBackend

logger = logging.getLogger(__name__)

class IdleManager:
    def __init__(self, backend: MidiBackend):
        self.backend = backend
        self._last_activity_time = time.time()
        self._is_idle = False
        self._manual_sleep = False
        self._has_notifications = False

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    def register_activity(self):
        """Called whenever a button is pressed or HA state changes."""
        self._last_activity_time = time.time()
        if self._is_idle:
            self.wake_up()

    def set_manual_sleep(self):
        """Manually trigger sleep mode."""
        logger.info("Manual sleep triggered")
        self._manual_sleep = True
        self.enter_idle()

    def set_notification_status(self, active: bool):
        """Update notification status and refresh wake button if idle."""
        if self._has_notifications != active:
            self._has_notifications = active
            if self._is_idle:
                self._update_wake_button()

    def check_status(self):
        """Check if we should enter idle mode based on timeout."""
        if self._is_idle:
            return

        elapsed = time.time() - self._last_activity_time
        if elapsed > IDLE_TIMEOUT:
            logger.info("Idle timeout (%.1fs) - Entering Sleep Mode", elapsed)
            self.enter_idle()

    def enter_idle(self):
        if self._is_idle:
            return
            
        self._is_idle = True
        
        # turn off all lights
        self._clear_all_leds()
        self._update_wake_button()

    def wake_up(self):
        logger.info("Waking up from Sleep Mode")
        self._is_idle = False
        self._manual_sleep = False
        
        # Controller will be responsible for refreshing LEDs after this returns

    def _clear_all_leds(self):
        # Clear main grid
        if self.backend and self.backend.is_connected():
            for note in range(128):
                if note != WAKE_BUTTON_ID:
                     self.backend.send_note(note, "off")

    def _update_wake_button(self):
        """Set wake button color based on notification status."""
        if not self.backend.is_connected():
            return
            
        if self._has_notifications:
            color = "orange_1"
        else:
            color = "green_2"
            
        self.backend.send_note(WAKE_BUTTON_ID, color)
