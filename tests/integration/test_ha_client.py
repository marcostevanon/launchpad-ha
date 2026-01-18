import pytest
import requests_mock
from src.ha_launchpad.infrastructure.ha.client import HomeAssistantClient

@pytest.fixture
def ha_client():
    return HomeAssistantClient("http://test.local", "token")

def test_get_state_success(ha_client):
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/states/light.test", json={"state": "on", "attributes": {}})
        
        state = ha_client.get_state("light.test")
        assert state["state"] == "on"

def test_get_state_404(ha_client):
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/states/light.test", status_code=404)
        
        state = ha_client.get_state("light.test")
        assert state == {"error": "not_found"}

def test_toggle_entity_light(ha_client):
    with requests_mock.Mocker() as m:
        m.post("http://test.local/api/services/light/toggle", status_code=200)
        
        success = ha_client.toggle_entity("light.test")
        assert success
        assert m.called

def test_volume_up(ha_client):
    with requests_mock.Mocker() as m:
        # Mock initial state get
        m.get("http://test.local/api/states/media_player.test", json={"state": "playing", "attributes": {"volume_level": 0.5}})
        # Mock volume set
        m.post("http://test.local/api/services/media_player/volume_set", status_code=200, additional_matcher=lambda r: round(r.json()['volume_level'], 2) == 0.57)
        
        success = ha_client.volume_up("media_player.test")
        assert success

def test_get_all_states(ha_client):
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/states", json=[
            {"entity_id": "light.test", "state": "on"},
            {"entity_id": "switch.test", "state": "off"}
        ])
        
        states = ha_client.get_all_states()
        assert len(states) == 2
        assert states[0]["entity_id"] == "light.test"
