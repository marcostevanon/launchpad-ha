from unittest.mock import MagicMock
from src.ha_launchpad.features.color_picker import ColorPicker

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
    
    # Should turn off palette
    color_picker.backend.send_note.assert_any_call(41, 'off') # checking one palette note

def test_handle_input_source_note_toggle(color_picker):
    color_picker.enter("light.test", 81)
    
    # Reset mocks
    color_picker.ha_client.reset_mock()
    
    # Press source note -> should toggle
    handled = color_picker.handle_input(81)
    
    assert handled
    assert not color_picker.active
    color_picker.ha_client.toggle_entity.assert_called_with("light.test")

def test_handle_input_palette_pick(color_picker):
    color_picker.enter("light.test", 81)
    
    # Reset mocks
    color_picker.ha_client.reset_mock()
    
    # Press palette note (e.g. 41 is red_1)
    handled = color_picker.handle_input(41)
    
    assert handled
    assert not color_picker.active
    
    # Should call turn_on with rgb
    color_picker.ha_client.call_service.assert_called()
    call_args = color_picker.ha_client.call_service.call_args
    assert call_args[0] == ("light", "turn_on", "light.test")
    assert "rgb_color" in call_args[1]

def test_handle_input_ignore_unmapped(color_picker):
    color_picker.enter("light.test", 81)
    
    # Press random note
    handled = color_picker.handle_input(999)
    
    # Should return True (swallowed) but stay active? 
    # Logic says: "Ignore other buttons while in this mode" and returns True
    assert handled
    assert color_picker.active
