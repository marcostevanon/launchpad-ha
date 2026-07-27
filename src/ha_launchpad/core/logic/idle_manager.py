import logging
import time
from collections.abc import Iterable

from ha_launchpad.config.mapping import ALL_PADS, IDLE_MODE_BUTTON_ID
from ha_launchpad.config.settings import IDLE_TIMEOUT, STANDBY_PREVIEW_DURATION
from ha_launchpad.infrastructure.midi.interface import MidiBackend

logger = logging.getLogger(__name__)

class IdleManager:
    def __init__(self, backend: MidiBackend):
        self.backend = backend
        self._last_activity_time = time.time()
        self._is_idle = False
        self._manual_sleep = False
        self._has_notifications = False
        # note -> time at which its standby preview should be turned back off
        self._preview_deadlines: dict[int, float] = {}

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
        self._forget_standby_preview()
        self._clear_all_leds()
        self._update_wake_button()

    def wake_up(self):
        logger.info("Waking up from Sleep Mode")
        self._is_idle = False
        self._manual_sleep = False
        # The caller repaints the whole board from scratch, so the preview
        # bookkeeping is no longer meaningful.
        self._forget_standby_preview()
        # Restart the clock. Without this the next check_status() still sees
        # the pre-sleep timestamp, decides the timeout has long since elapsed,
        # and puts the board straight back to sleep.
        self._last_activity_time = time.time()


        # Controller will be responsible for refreshing LEDs after this returns

    def show_standby_preview(self, changes: Iterable[tuple[int, str, int]]) -> None:
        """Light the pads whose entities just changed, without leaving sleep.

        Turning a lamp on from a wall switch should be visible on a sleeping
        board, but it is not a reason to wake the whole thing up. The pads
        light for STANDBY_PREVIEW_DURATION and then go dark again.
        """
        if not self.backend.is_connected():
            return

        deadline = time.time() + STANDBY_PREVIEW_DURATION
        shown = 0
        for note, color, channel in changes:
            # The wake button owns its own colour while asleep.
            if note == IDLE_MODE_BUTTON_ID:
                continue
            self.backend.send_note(note, color, channel)
            self._preview_deadlines[note] = deadline
            shown += 1

        if shown:
            logger.info(
                "Standby preview: %d pad(s) lit for %.0fs", shown, STANDBY_PREVIEW_DURATION
            )

    def expire_standby_preview(self) -> None:
        """Turn off any preview pads whose time is up."""
        if not self._preview_deadlines:
            return

        now = time.time()
        expired = [note for note, due in self._preview_deadlines.items() if now >= due]
        for note in expired:
            self.backend.send_note(note, "off")
            del self._preview_deadlines[note]

        if expired:
            logger.debug("Standby preview expired for %d pad(s)", len(expired))

    def _forget_standby_preview(self) -> None:
        self._preview_deadlines.clear()

    def _clear_all_leds(self):
        # Clear main grid
        if self.backend and self.backend.is_connected():
            for note in ALL_PADS:
                if note != IDLE_MODE_BUTTON_ID:
                     self.backend.send_note(note, "off")

    def _update_wake_button(self):
        """Set wake button color based on notification status."""
        if not self.backend.is_connected():
            return
            
        if self._has_notifications:
            color = "orange_1"
        else:
            color = "lightblue_0"
            
        self.backend.send_note(IDLE_MODE_BUTTON_ID, color)
