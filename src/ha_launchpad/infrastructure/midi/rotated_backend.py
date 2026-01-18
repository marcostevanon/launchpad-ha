from typing import Optional, Any
from src.ha_launchpad.utils.rotate_pad import rotate_pad, inverse_rotation
from .interface import MidiBackend

class RotatedMidiIn:
    """Wrapper for MIDI input iterator that rotates incoming notes."""
    def __init__(self, midi_in_port, rotation: int):
        self._midi_in_port = midi_in_port
        self._rotation = rotation

    def iter_pending(self):
        """Iterate over pending messages and rotate their notes."""
        if not hasattr(self._midi_in_port, "iter_pending"):
            return iter(())
            
        for msg in self._midi_in_port.iter_pending():
            yield self._rotate_msg(msg)

    def __iter__(self):
        # Support direct iteration if needed
        for msg in self._midi_in_port:
            yield self._rotate_msg(msg)

    def _rotate_msg(self, msg):
        if hasattr(msg, "note"):
            # Rotate from physical to logical
            msg.note = rotate_pad(msg.note, self._rotation)
        return msg


class RotatedBackend(MidiBackend):
    """
    Decorator for a MidiBackend that automatically handles note rotation.
    
    Any note sent TO this backend will be rotated from 'logical' to 'physical'.
    Any message received FROM this backend will be rotated from 'physical' to 'logical'.
    """
    def __init__(self, backend: MidiBackend, rotation: int):
        self._backend = backend
        self._rotation = rotation
        self._inv_rotation = inverse_rotation(rotation)

    def find_and_open(self) -> bool:
        return self._backend.find_and_open()

    def send_note(self, note: int, color: str, channel: int = 0) -> None:
        # Rotate from logical to physical
        physical_note = rotate_pad(note, self._inv_rotation)
        self._backend.send_note(physical_note, color, channel)

    def iter_incoming(self) -> Optional[Any]:
        source = self._backend.iter_incoming()
        if source is None:
            return None
        return RotatedMidiIn(source, self._rotation)

    def is_connected(self) -> bool:
        return self._backend.is_connected()

    def close(self) -> None:
        self._backend.close()
