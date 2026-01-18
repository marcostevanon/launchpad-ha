import time
import logging
from typing import Optional
from src.ha_launchpad.infrastructure.midi.interface import MidiBackend

logger = logging.getLogger(__name__)

class FeedbackManager:
    def __init__(self, backend: MidiBackend):
        self.backend = backend

    def flash(self, note: int, color: str, duration: float = 0.2):
        """Flash a button for a short duration."""
        self.backend.send_note(note, color, channel=2)
        time.sleep(duration)

    def pulse(self, note: int, color: str, duration: float = 0.4, clear_note: Optional[int] = None):
        """Pulse a button, optionally clearing another button."""
        self.backend.send_note(note, color, channel=2)
        
        if clear_note is not None:
             self.backend.send_note(clear_note, "off")
             
        time.sleep(duration)

    def clear(self, note: int):
        self.backend.send_note(note, "off")
