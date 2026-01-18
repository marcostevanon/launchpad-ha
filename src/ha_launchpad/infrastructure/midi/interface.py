from abc import ABC, abstractmethod
from typing import Optional, Any

class MidiBackend(ABC):
    @abstractmethod
    def find_and_open(self) -> bool:
        """Find and open the MIDI ports."""
        pass

    @abstractmethod
    def send_note(self, note: int, color: str, channel: int = 0) -> None:
        """Send a note on message."""
        pass

    @abstractmethod
    def iter_incoming(self) -> Optional[Any]:
        """Return an iterator for incoming messages."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the device is connected."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        pass
