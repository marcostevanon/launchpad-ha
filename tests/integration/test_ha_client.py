import pytest
import requests_mock

from ha_launchpad.infrastructure.ha.client import (
    HomeAssistantClient,
    HomeAssistantUnauthorized,
)


@pytest.fixture
def ha_client():
    return HomeAssistantClient("http://test.local", "token")


def test_get_state_success(ha_client):
    with requests_mock.Mocker() as m:
        m.get(
            "http://test.local/api/states/light.test",
            json={"state": "on", "attributes": {}},
        )

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


def test_toggle_entity_script(ha_client):
    with requests_mock.Mocker() as m:
        m.post("http://test.local/api/services/script/turn_on", status_code=200)

        success = ha_client.toggle_entity("script.vinyl_play_on_sonos")
        assert success
        assert m.called


def test_volume_up(ha_client):
    with requests_mock.Mocker() as m:
        # Mock initial state get
        m.get(
            "http://test.local/api/states/media_player.test",
            json={"state": "playing", "attributes": {"volume_level": 0.5}},
        )
        # Mock volume set
        m.post(
            "http://test.local/api/services/media_player/volume_set",
            status_code=200,
            additional_matcher=lambda r: round(r.json()["volume_level"], 2) == 0.57,
        )

        success = ha_client.volume_up("media_player.test")
        assert success


def test_server_error_gives_up_instead_of_looping(ha_client):
    """A non-404 HTTP error used to fall out of the except block and re-issue
    the request immediately, with no sleep and no attempt cap -- an unthrottled
    hot loop against Home Assistant that never returned to the caller."""
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/states", status_code=500)

        states = ha_client.get_all_states()

        assert states == []
        assert m.call_count == 1


def test_unauthorized_is_raised_not_retried(ha_client):
    """A rejected token cannot be fixed by retrying, and repeated attempts can
    trip Home Assistant's IP ban."""
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/states", status_code=401, text="bad token")

        with pytest.raises(HomeAssistantUnauthorized):
            ha_client.get_all_states()

        assert m.call_count == 1


def test_service_call_failure_returns_false(ha_client):
    with requests_mock.Mocker() as m:
        m.post("http://test.local/api/services/light/toggle", status_code=503)

        assert ha_client.toggle_entity("light.test") is False


def test_is_available_when_api_answers(ha_client):
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/", json={"message": "API running."})

        assert ha_client.is_available()


def test_is_available_false_when_endpoint_missing(ha_client):
    """A 404 used to read as "connected": get_state returned the truthy dict
    {"error": "not_found"}, which the startup probe accepted."""
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/", status_code=404)

        assert not ha_client.is_available()


def test_is_available_false_on_unexpected_body(ha_client):
    with requests_mock.Mocker() as m:
        m.get("http://test.local/api/", json={"message": "nope"})

        assert not ha_client.is_available()


def test_get_all_states(ha_client):
    with requests_mock.Mocker() as m:
        m.get(
            "http://test.local/api/states",
            json=[
                {"entity_id": "light.test", "state": "on"},
                {"entity_id": "switch.test", "state": "off"},
            ],
        )

        states = ha_client.get_all_states()
        assert len(states) == 2
        assert states[0]["entity_id"] == "light.test"
