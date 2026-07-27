import pytest
from unittest.mock import MagicMock
from ha_launchpad.config.mapping import ALL_PADS
from ha_launchpad.infrastructure.midi.rotated_backend import RotatedBackend

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

@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_every_pad_stays_a_valid_midi_note_when_rotated(rotation):
    """Rotation must map the grid onto itself, whatever the angle.

    Sweeping `range(128)` instead used to push notes 100-127 through the 180
    degree transform and yield -1 to -28, which the MIDI layer rejected one
    warning at a time.
    """
    inner_backend = MagicMock()
    rotated = RotatedBackend(inner_backend, rotation)

    for pad in ALL_PADS:
        rotated.send_note(pad, "green_1")

    sent = [call.args[0] for call in inner_backend.send_note.call_args_list]
    assert len(sent) == 64
    assert all(0 <= note <= 127 for note in sent)
    assert set(sent) == set(ALL_PADS)


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
