import logging
import time

from ha_launchpad.infrastructure.midi.interface import MidiBackend

logger = logging.getLogger(__name__)

# Channel 3 on the wire (mido counts from zero) is the Launchpad's pulsing
# lighting mode, per Novation's programmer reference. Channel 1 would be
# flashing, which the app deliberately does not use.
PULSE_CHANNEL = 2


class FeedbackManager:
    def __init__(self, backend: MidiBackend):
        self.backend = backend

    def pulse(
        self,
        note: int,
        color: str,
        duration: float = 0.4,
        clear_note: int | None = None,
    ):
        """Pulse a button, optionally clearing another button.

        This used to have a `flash()` twin that claimed to do something
        different but sent the identical message on the identical channel.
        """
        self.backend.send_note(note, color, channel=PULSE_CHANNEL)

        if clear_note is not None:
            self.backend.send_note(clear_note, "off")

        time.sleep(duration)

    def clear(self, note: int):
        self.backend.send_note(note, "off")
