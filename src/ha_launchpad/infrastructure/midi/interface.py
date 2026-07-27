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
    def iter_incoming(self) -> Any | None:
        """Return an iterator for incoming messages."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the device is connected."""

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
