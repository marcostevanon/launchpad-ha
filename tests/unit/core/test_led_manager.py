from unittest.mock import MagicMock

import pytest

from ha_launchpad.core.logic.led_manager import LEDManager


@pytest.fixture
def led_manager():
    disco = MagicMock()
    disco.active = False
    return LEDManager(MagicMock(), MagicMock(), {81: "light.a"}, disco)


def _states(state):
    return [{"entity_id": "light.a", "state": state, "attributes": {"brightness": 255}}]


def test_dry_run_reports_the_change_without_emitting(led_manager):
    led_manager.ha_client.get_all_states.return_value = _states("on")

    changed, _ = led_manager.update_all(dry_run=True)

    assert changed
    led_manager.backend.send_note.assert_not_called()


def test_dry_run_does_not_consume_the_change(led_manager):
    """A dry run must not bank the new state as though it had been painted.

    While the board is asleep every poll is a dry run. If those runs updated
    the cache, the repaint on wake would find nothing to send and the board
    would come back blank -- lighting up only pads that happened to change
    afterwards.
    """
    led_manager.ha_client.get_all_states.return_value = _states("on")

    led_manager.update_all(dry_run=True)
    changed, _ = led_manager.update_all(dry_run=False)

    assert changed
    led_manager.backend.send_note.assert_called_once_with(81, "green_1", 0)


def test_unchanged_state_is_not_resent(led_manager):
    led_manager.ha_client.get_all_states.return_value = _states("on")

    led_manager.update_all(dry_run=False)
    led_manager.backend.send_note.reset_mock()
    changed, _ = led_manager.update_all(dry_run=False)

    assert not changed
    led_manager.backend.send_note.assert_not_called()


def test_commit_stops_a_change_being_reported_twice(led_manager):
    """The standby preview paints the board itself, then commits, so the next
    poll does not keep re-reporting the same change forever."""
    led_manager.ha_client.get_all_states.return_value = _states("on")

    changes, _ = led_manager.update_all(dry_run=True)
    assert changes

    led_manager.commit(changes)
    changes_again, _ = led_manager.update_all(dry_run=True)

    assert changes_again == []


def test_failed_fetch_leaves_the_board_alone(led_manager):
    led_manager.ha_client.get_all_states.return_value = []

    changed, has_notifications = led_manager.update_all(dry_run=False)

    assert not changed
    assert not has_notifications
    led_manager.backend.send_note.assert_not_called()


def test_outage_is_reported_once_not_every_poll(led_manager, caplog):
    led_manager.ha_client.get_all_states.return_value = []

    with caplog.at_level("WARNING"):
        for _ in range(5):
            led_manager.update_all(dry_run=False)

    warnings = [r for r in caplog.records if "No states returned" in r.message]
    assert len(warnings) == 1


def test_outage_warning_rearms_after_recovery(led_manager, caplog):
    with caplog.at_level("WARNING"):
        led_manager.ha_client.get_all_states.return_value = []
        led_manager.update_all(dry_run=False)

        led_manager.ha_client.get_all_states.return_value = _states("on")
        led_manager.update_all(dry_run=False)

        led_manager.ha_client.get_all_states.return_value = []
        led_manager.update_all(dry_run=False)

    warnings = [r for r in caplog.records if "No states returned" in r.message]
    assert len(warnings) == 2


def test_unavailable_is_not_rendered_as_off():
    """A bulb killed at the wall switch reports `unavailable`. It used to be
    coloured exactly like one that was simply switched off."""
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(MagicMock(), MagicMock(), {81: "light.a"}, disco)
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "light.a", "state": "unavailable", "attributes": {}}
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(81, "gray_1", 0)]


def test_volume_pad_greys_out_when_its_player_is_unavailable():
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(MagicMock(), MagicMock(), {66: "volume_up.media_player.x"}, disco)
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "media_player.x", "state": "unavailable", "attributes": {}}
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(66, "gray_1", 0)]


def test_volume_pad_greys_out_when_the_player_reports_no_level():
    """A TV that is off has no volume_level, so the service call would fail."""
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(
        MagicMock(), MagicMock(), {56: "volume_down.media_player.tv"}, disco
    )
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "media_player.tv", "state": "off", "attributes": {}}
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(56, "gray_1", 0)]


def test_volume_pad_is_active_when_a_level_is_reported():
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(MagicMock(), MagicMock(), {56: "volume_down.media_player.x"}, disco)
    lm.ha_client.get_all_states.return_value = [
        {
            "entity_id": "media_player.x",
            "state": "idle",
            "attributes": {"volume_level": 0.4},
        }
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(56, "purple_1", 0)]
