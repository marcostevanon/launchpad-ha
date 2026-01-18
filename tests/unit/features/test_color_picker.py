import pytest
from unittest.mock import MagicMock
from src.ha_launchpad.features.color_picker import ColorPicker
from src.ha_launchpad.config.mapping import BRIGHTNESS_PALETTE

@pytest.fixture
def color_picker():
    ha_client = MagicMock()
    backend = MagicMock()
    return ColorPicker(ha_client, backend)

def test_initial_state(color_picker):
    assert not color_picker.active
    assert color_picker.target_entity is None

def test_enter_mode(color_picker):
    color_picker.enter("light.test", 81)
    assert color_picker.active
    assert color_picker.target_entity == "light.test"
    assert color_picker.source_note == 81
    
    # Should show palette
    assert color_picker.backend.send_note.call_count >= 1

def test_exit_mode(color_picker):
    color_picker.enter("light.test", 81)
    color_picker.exit()
    assert not color_picker.active
    assert color_picker.target_entity is None
    
    # Should turn off palettes
    color_picker.backend.send_note.assert_any_call(41, 'off') # color note
    color_picker.backend.send_note.assert_any_call(21, 'off') # brightness note

def test_handle_input_brightness_pick(color_picker):
    color_picker.enter("light.test", 81)
    
    # Reset mocks
    color_picker.ha_client.reset_mock()
    
    # Press brightness note (e.g. 21 is 0.1)
    res = color_picker.handle_input(21)
    
    assert isinstance(res, dict)
    assert res["source_note"] == 81
    assert res["pulse_color"] == "white"
    assert not color_picker.active
    
    # Should call turn_on with brightness
    color_picker.ha_client.call_service.assert_called_with(
        "light", "turn_on", "light.test", brightness=int(0.1 * 255)
    )

def test_handle_input_source_note_toggle(color_picker):
    color_picker.enter("light.test", 81)
    
    # Reset mocks
    color_picker.ha_client.reset_mock()
    
    # Press source note -> should toggle
    res = color_picker.handle_input(81)
    
    assert isinstance(res, dict)
    assert res["source_note"] == 81
    assert res["pulse_color"] is None
    assert not color_picker.active
    color_picker.ha_client.toggle_entity.assert_called_with("light.test")

def test_handle_input_palette_pick(color_picker):
    color_picker.enter("light.test", 81)
    
    # Reset mocks
    color_picker.ha_client.reset_mock()
    
    # Press palette note (e.g. 41 is red_1)
    res = color_picker.handle_input(41)
    
    assert isinstance(res, dict)
    assert res["source_note"] == 81
    assert res["pulse_color"] is not None
    assert not color_picker.active
    
    # Should call turn_on with rgb
    color_picker.ha_client.call_service.assert_called()
    call_args = color_picker.ha_client.call_service.call_args
    assert call_args[0] == ("light", "turn_on", "light.test")
    assert "rgb_color" in call_args[1]

def test_handle_input_ignore_unmapped(color_picker):
    color_picker.enter("light.test", 81)
    
    # Press random note
    res = color_picker.handle_input(999)
    
    # Should return -1 (swallowed) but stay active
    assert res == -1
    assert color_picker.active
