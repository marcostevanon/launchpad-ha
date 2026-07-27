"""A mock MIDI backend used for development without hardware."""

import logging
from typing import Any

from .interface import MidiBackend

logger = logging.getLogger(__name__)


class MockMidiPort:
    """Mock MIDI port that mimics mido's port interface."""

    def __iter__(self):
        return self

    def __next__(self):
        # Simulate blocking or just raise StopIteration for now
        # Ideally we might want to inject messages here for testing
        raise StopIteration

    def iter_pending(self):
        """Return an empty iterator (no pending messages)."""
        return iter(())

    def close(self):
        """Mock close method."""


class MockBackend(MidiBackend):
    def __init__(self, ident: str | None = None):
        self.ident = ident or "MOCK"
        self.midi_in = None
        self.midi_out = None

    def find_and_open(self) -> bool:
        # Mock always available for local development
        self.midi_in = MockMidiPort()
        self.midi_out = None
        return True

    def send_note(self, note: int, color: str, channel: int = 0):
        # No-op or debug log for development
        logger.debug(
            "[MOCK] send_note note=%s color=%s channel=%s", note, color, channel
        )

    def iter_incoming(self) -> Any | None:
        return self.midi_in

    def is_connected(self) -> bool:
        """Check if the mock device is available (always True for mock)."""
        return True

    def close(self):
        pass
