from itertools import pairwise
from unittest.mock import MagicMock

import pytest

from ha_launchpad.config.settings import DISCO_LIGHTS, DISCO_TRANSITION
from ha_launchpad.features.disco import DiscoMode


@pytest.fixture
def disco():
    d = DiscoMode(MagicMock())
    yield d
    d.stop()


def _colour_calls(client):
    return [c for c in client.call_service.call_args_list if "hs_color" in c.kwargs]


def test_brightness_is_set_once_at_start_not_per_step(disco):
    """The Trådfri integration gives its single transition_time to the first
    attribute command. If brightness rides along with every colour change it
    takes the transition and the colour hard-cuts."""
    disco.start()
    disco._stop_event.wait(0.3)
    disco.stop()

    brightness_calls = [
        c
        for c in disco.ha_client.call_service.call_args_list
        if "brightness" in c.kwargs
    ]
    assert len(brightness_calls) == len(DISCO_LIGHTS)

    colour_calls = _colour_calls(disco.ha_client)
    assert colour_calls, "expected at least one colour step"
    assert all("brightness" not in c.kwargs for c in colour_calls)


def test_every_colour_step_requests_a_crossfade(disco):
    disco.start()
    disco._stop_event.wait(0.3)
    disco.stop()

    for call in _colour_calls(disco.ha_client):
        assert call.kwargs["transition"] == DISCO_TRANSITION
        # Whole seconds only: int() truncation would silently disable the fade.
        assert isinstance(call.kwargs["transition"], int)
        assert call.kwargs["transition"] >= 1


def test_hue_steps_are_bounded(disco):
    """Random jumps across the colour wheel look like cuts even with a
    crossfade; bounded steps sweep through intermediate hues."""
    disco.start()
    disco._stop_event.wait(0.6)
    disco.stop()

    per_light = {}
    for call in _colour_calls(disco.ha_client):
        light = call.args[2]
        per_light.setdefault(light, []).append(call.kwargs["hs_color"][0])

    for hues in per_light.values():
        for previous, current in pairwise(hues):
            step = (current - previous) % 360.0
            assert 40.0 <= step <= 110.0


def test_lights_are_never_turned_off_mid_effect(disco):
    """Turning a bulb off is a hard cut by definition, and on Trådfri it also
    resets brightness to 1 for the next turn-on."""
    disco.start()
    disco._stop_event.wait(0.3)
    disco.stop()

    assert all(
        c.args[1] != "turn_off" for c in disco.ha_client.call_service.call_args_list
    )
