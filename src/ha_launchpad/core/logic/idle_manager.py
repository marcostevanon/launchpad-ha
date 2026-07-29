import logging
import time
from collections.abc import Iterable

from ha_launchpad.config.mapping import ALL_PADS, IDLE_MODE_BUTTON_ID
from ha_launchpad.config.settings import IDLE_TIMEOUT, STANDBY_PREVIEW_DURATION
from ha_launchpad.infrastructure.midi.interface import MidiBackend

logger = logging.getLogger(__name__)

# The sleeping board shows exactly two things: this button, and any pad whose
# entity needs attention.
WAKE_BUTTON_COLOR = "white"


class IdleManager:
    def __init__(self, backend: MidiBackend):
        self.backend = backend
        self._last_activity_time = time.time()
        self._is_idle = False
        self._manual_sleep = False
        # note -> (colour, channel) for pads held lit through sleep because the
        # thing behind them needs attention.
        self._notification_pads: dict[int, tuple[str, int]] = {}
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

    def sync_notification_pads(self, pads: Iterable[tuple[int, str, int]]) -> None:
        """Hold the pads that need attention lit while the board sleeps.

        A plant below its moisture threshold is worth seeing on a dark board,
        and it is worth seeing on the pad that owns it rather than as a single
        summary light somewhere else. These pads survive the sleep blackout and
        ignore the standby preview timer; they go out when the problem does.
        """
        if not self.backend.is_connected():
            return

        wanted = {
            note: (color, channel)
            for note, color, channel in pads
            # The wake button is a control, not a status light.
            if note != IDLE_MODE_BUTTON_ID
        }

        for note in self._notification_pads.keys() - wanted.keys():
            self.backend.send_note(note, "off")
            logger.info("Notification cleared on pad %d", note)

        for note, (color, channel) in wanted.items():
            if self._notification_pads.get(note) != (color, channel):
                self.backend.send_note(note, color, channel)
                logger.info("Notification held on pad %d (%s)", note, color)
            # A held pad outranks a preview: drop any pending expiry so the
            # preview timer cannot switch it back off underneath us.
            self._preview_deadlines.pop(note, None)

        self._notification_pads = wanted

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
        # The blackout below darkens the notification pads too. Forgetting them
        # here makes the next sync repaint them instead of believing they are
        # already lit; the poll that enters sleep runs that sync immediately
        # afterwards, so the gap is not visible.
        self._forget_notification_pads()
        self._clear_all_leds()
        self._update_wake_button()

    def wake_up(self):
        logger.info("Waking up from Sleep Mode")
        self._is_idle = False
        self._manual_sleep = False
        # The caller repaints the whole board from scratch, so the preview and
        # notification bookkeeping is no longer meaningful.
        self._forget_standby_preview()
        self._forget_notification_pads()
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
            # Already held lit as a notification, and it must not inherit an
            # expiry that would darken it two minutes later.
            if note in self._notification_pads:
                continue
            self.backend.send_note(note, color, channel)
            self._preview_deadlines[note] = deadline
            shown += 1

        if shown:
            logger.info(
                "Standby preview: %d pad(s) lit for %.0fs",
                shown,
                STANDBY_PREVIEW_DURATION,
            )

    def expire_standby_preview(self) -> None:
        """Turn off any preview pads whose time is up."""
        if not self._preview_deadlines:
            return

        now = time.time()
        expired = [note for note, due in self._preview_deadlines.items() if now >= due]
        for note in expired:
            # A pad that became a notification while its preview was running
            # stays lit; only the timer is dropped.
            if note not in self._notification_pads:
                self.backend.send_note(note, "off")
            del self._preview_deadlines[note]

        if expired:
            logger.debug("Standby preview expired for %d pad(s)", len(expired))

    def _forget_standby_preview(self) -> None:
        self._preview_deadlines.clear()

    def _forget_notification_pads(self) -> None:
        """Drop the bookkeeping without touching the board.

        Called around the blackout and the wake-up repaint, both of which
        repaint every pad themselves. Sending "off" here would fight them.
        """
        self._notification_pads.clear()

    def _clear_all_leds(self):
        # Clear main grid
        if self.backend and self.backend.is_connected():
            for note in ALL_PADS:
                if note != IDLE_MODE_BUTTON_ID:
                    self.backend.send_note(note, "off")

    def _update_wake_button(self):
        """Paint the wake button.

        One job, one colour. It used to double as a summary alert light,
        turning orange when anything needed attention, which meant the board
        told you that something was wrong without telling you what. The pads
        themselves now carry that, so this is just the way back in.
        """
        if not self.backend.is_connected():
            return

        self.backend.send_note(IDLE_MODE_BUTTON_ID, WAKE_BUTTON_COLOR)
