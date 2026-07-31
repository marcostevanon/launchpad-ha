from abc import ABC, abstractmethod
from typing import Any


class MidiBackend(ABC):
    @abstractmethod
    def find_and_open(self) -> bool:
        """Find and open the MIDI ports."""

    @abstractmethod
    def send_note(self, note: int, color: str, channel: int = 0) -> None:
        """Send a note on message."""

    @abstractmethod
    def send_velocity(self, note: int, velocity: int, channel: int = 0) -> None:
        """Light a grid pad with a raw palette entry, 0-127.

        `send_note` covers the named colours the rest of the app uses. This is
        for the colour lab, which addresses all 128 and has no names for them.
        """

    @abstractmethod
    def send_cc(self, control: int, velocity: int, channel: int = 0) -> None:
        """Light one of the buttons around the grid with a raw palette entry.

        The top row and the right-hand column are Control Changes, not notes,
        and they sit outside the 8x8 grid, so they are never rotated.
        """

    @abstractmethod
    def iter_incoming(self) -> Any | None:
        """Return an iterator for incoming messages."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the device is connected."""

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
