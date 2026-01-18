import pytest
from unittest.mock import MagicMock
from src.ha_launchpad.infrastructure.midi.rotated_backend import RotatedBackend

class MockMsg:
    def __init__(self, note):
        self.note = note
        self.type = "note_on"

def test_rotated_backend_send():
    inner_backend = MagicMock()
    # 180 deg rotation: (9-row)*10 + (9-col)
    # 81 (8,1) -> (9-8, 9-1) = (1,8) -> 18
    rotated = RotatedBackend(inner_backend, 180)
    
    rotated.send_note(81, "green_1")
    
    inner_backend.send_note.assert_called_with(18, "green_1", 0)

def test_rotated_backend_receive():
    inner_backend = MagicMock()
    rotated = RotatedBackend(inner_backend, 180)
    
    # Simulate hardware sending 18 (physical)
    mock_port = MagicMock()
    mock_port.iter_pending.return_value = [MockMsg(18)]
    inner_backend.iter_incoming.return_value = mock_port
    
    rotated_in = rotated.iter_incoming()
    msgs = list(rotated_in.iter_pending())
    
    assert len(msgs) == 1
    assert msgs[0].note == 81 # Should be rotated back to logical
