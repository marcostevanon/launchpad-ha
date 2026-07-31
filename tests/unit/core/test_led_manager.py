from unittest.mock import MagicMock

import pytest

from ha_launchpad.config.mapping import COLORS
from ha_launchpad.config.palette import PALETTE_HEX
from ha_launchpad.core.logic.led_manager import (
    OFF_COLOR,
    UNAVAILABLE_COLOR,
    LEDManager,
)


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

    assert changes == [(81, UNAVAILABLE_COLOR, 0)]


def test_an_entity_that_does_not_exist_is_treated_as_unavailable(led_manager):
    """A pad mapped to something Home Assistant has never heard of used to
    glow red and still fire service calls. It cannot control anything, so it
    belongs in the same bucket as an unreachable device."""
    led_manager.ha_client.get_all_states.return_value = [
        {"entity_id": "light.something_else", "state": "on", "attributes": {}}
    ]

    changes, _ = led_manager.update_all(dry_run=False)

    assert changes == [(81, UNAVAILABLE_COLOR, 0)]
    assert led_manager.is_unavailable(81)


def test_a_missing_entity_is_reported_once_not_every_poll(led_manager, caplog):
    led_manager.ha_client.get_all_states.return_value = [
        {"entity_id": "light.something_else", "state": "on", "attributes": {}}
    ]

    with caplog.at_level("WARNING"):
        for _ in range(5):
            led_manager.update_all(dry_run=False)

    warnings = [r for r in caplog.records if "does not exist" in r.message]
    assert len(warnings) == 1


def test_a_missing_entity_recovers_once_it_appears(led_manager):
    """Creating the script in Home Assistant must light its pad without a
    restart of the controller."""
    led_manager.ha_client.get_all_states.return_value = [
        {"entity_id": "light.something_else", "state": "on", "attributes": {}}
    ]
    led_manager.update_all(dry_run=False)

    led_manager.ha_client.get_all_states.return_value = [
        {"entity_id": "light.a", "state": "on", "attributes": {"brightness": 255}}
    ]
    changes, _ = led_manager.update_all(dry_run=False)

    assert changes == [(81, "green_1", 0)]
    assert not led_manager.is_unavailable(81)


def _gated_manager():
    """A pad pointing at a script, which is the case the gate exists for.

    A script entity is present whether or not the machine it drives has power,
    so the pad looks live no matter what and pressing it can only fail.
    """
    disco = MagicMock()
    disco.active = False
    return LEDManager(MagicMock(), MagicMock(), {45: "script.do_a_thing"}, disco)


def test_pad_greys_out_when_the_thing_behind_it_is_powered_off(monkeypatch):
    monkeypatch.setattr(
        "ha_launchpad.core.logic.led_manager.PAD_AVAILABILITY",
        {45: "binary_sensor.the_machine"},
    )
    lm = _gated_manager()
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "script.do_a_thing", "state": "off", "attributes": {}},
        {"entity_id": "binary_sensor.the_machine", "state": "off", "attributes": {}},
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(45, UNAVAILABLE_COLOR, 0)]
    assert lm.is_unavailable(45)


def test_pad_lights_normally_once_the_dependency_is_up(monkeypatch):
    monkeypatch.setattr(
        "ha_launchpad.core.logic.led_manager.PAD_AVAILABILITY",
        {45: "binary_sensor.the_machine"},
    )
    lm = _gated_manager()
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "script.do_a_thing", "state": "off", "attributes": {}},
        {"entity_id": "binary_sensor.the_machine", "state": "on", "attributes": {}},
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(45, "sage", 0)]
    assert not lm.is_unavailable(45)


def test_a_missing_gate_entity_closes_the_pad(monkeypatch):
    """Better a dead pad than one that fires a call which cannot work."""
    monkeypatch.setattr(
        "ha_launchpad.core.logic.led_manager.PAD_AVAILABILITY",
        {45: "binary_sensor.typo"},
    )
    lm = _gated_manager()
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "script.do_a_thing", "state": "off", "attributes": {}}
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(45, UNAVAILABLE_COLOR, 0)]


def test_pads_without_a_gate_are_untouched(monkeypatch):
    monkeypatch.setattr(
        "ha_launchpad.core.logic.led_manager.PAD_AVAILABILITY",
        {45: "binary_sensor.the_machine"},
    )
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(MagicMock(), MagicMock(), {81: "light.a"}, disco)
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "light.a", "state": "on", "attributes": {"brightness": 255}}
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(81, "green_1", 0)]


def test_idle_player_with_an_empty_queue_greys_out():
    """It looked identical to a paused player, so it invited a press that
    could only come back as an HTTP 500."""
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(MagicMock(), MagicMock(), {55: "media_player.speaker"}, disco)
    lm.ha_client.get_all_states.return_value = [
        {
            "entity_id": "media_player.speaker",
            "state": "idle",
            "attributes": {"volume_level": 0.19, "source": "Music Assistant Queue"},
        }
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(55, UNAVAILABLE_COLOR, 0)]
    assert lm.is_unavailable(55)


def test_paused_player_stays_lit():
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(MagicMock(), MagicMock(), {55: "media_player.speaker"}, disco)
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "media_player.speaker", "state": "paused", "attributes": {}}
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(55, OFF_COLOR, 0)]
    assert not lm.is_unavailable(55)


def test_volume_pad_greys_out_when_its_player_is_unavailable():
    disco = MagicMock()
    disco.active = False
    lm = LEDManager(MagicMock(), MagicMock(), {66: "volume_up.media_player.x"}, disco)
    lm.ha_client.get_all_states.return_value = [
        {"entity_id": "media_player.x", "state": "unavailable", "attributes": {}}
    ]

    changes, _ = lm.update_all(dry_run=False)

    assert changes == [(66, UNAVAILABLE_COLOR, 0)]


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

    assert changes == [(56, UNAVAILABLE_COLOR, 0)]


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


@pytest.fixture
def plant_manager():
    disco = MagicMock()
    disco.active = False
    return LEDManager(MagicMock(), MagicMock(), {81: "plant.monstera"}, disco)


def _plant(problem):
    return [
        {
            "entity_id": "plant.monstera",
            "state": "problem" if problem != "none" else "ok",
            "attributes": {"problem": problem},
        }
    ]


def test_notification_pads_names_the_pad_not_just_the_fact(plant_manager):
    plant_manager.ha_client.get_all_states.return_value = _plant("moisture low")

    _, has_notifications = plant_manager.update_all(dry_run=False)

    assert has_notifications
    assert plant_manager.notification_pads == [(81, "red_2", 2)]


def test_notification_pads_survive_a_dry_run(plant_manager):
    """Every poll is a dry run while the board sleeps, which is exactly when
    the sleeping board needs to know which pads to hold lit."""
    plant_manager.ha_client.get_all_states.return_value = _plant("moisture low")

    plant_manager.update_all(dry_run=True)

    assert plant_manager.notification_pads == [(81, "red_2", 2)]
    plant_manager.backend.send_note.assert_not_called()


def test_healthy_plant_reports_no_notification_pads(plant_manager):
    plant_manager.ha_client.get_all_states.return_value = _plant("none")

    _, has_notifications = plant_manager.update_all(dry_run=False)

    assert not has_notifications
    assert plant_manager.notification_pads == []


def test_unreachable_is_dimmer_than_merely_switched_off():
    """The rule both colours were chosen under, on the hardware. An unreachable
    device is a passive fact: it must never outshine one that is simply off,
    which is what happened the last time these were picked off a screen."""

    def luminance(name):
        r, g, b = bytes.fromhex(PALETTE_HEX[COLORS[name]][1:])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    assert luminance(UNAVAILABLE_COLOR) < luminance(OFF_COLOR)
