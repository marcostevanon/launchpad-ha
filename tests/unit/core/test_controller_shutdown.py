import os
import signal
from unittest.mock import MagicMock

import pytest

from ha_launchpad.core.controller import LaunchpadController


@pytest.fixture(autouse=True)
def restore_signal_handlers():
    """Keep the test session's own handlers intact."""
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    yield
    for sig, handler in saved.items():
        signal.signal(sig, handler)


@pytest.fixture
def controller():
    return LaunchpadController(MagicMock(), {}, backend=MagicMock())


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT])
def test_signal_requests_graceful_shutdown(controller, sig):
    controller.running = True
    controller._install_signal_handlers()

    os.kill(os.getpid(), sig)

    assert controller.running is False


def test_exits_non_zero_when_the_launchpad_is_never_found(monkeypatch):
    backend = MagicMock()
    backend.find_and_open.return_value = False
    backend.is_connected.return_value = False
    controller = LaunchpadController(MagicMock(), {}, backend=backend)

    monkeypatch.setattr("ha_launchpad.core.controller.time.sleep", lambda *_: None)

    with pytest.raises(SystemExit) as exit_info:
        controller.run()

    assert exit_info.value.code == 1
    backend.close.assert_called()


def test_handlers_are_installed_for_both_signals(controller):
    controller._install_signal_handlers()

    for sig in (signal.SIGTERM, signal.SIGINT):
        assert callable(signal.getsignal(sig))
        assert signal.getsignal(sig) not in (signal.SIG_DFL, signal.SIG_IGN)


def test_pressing_an_unavailable_pad_does_nothing_but_blank_it(controller):
    """An unreachable device cannot be controlled, so the pad must not enter
    colour-pick mode (which pulsed yellow) or fire a service call."""
    # Bypass the rotation decorator so the assertion is about controller
    # behaviour, not about which physical pad the note lands on.
    controller.backend = MagicMock()
    controller.led_manager._unavailable_notes = {81}
    controller.button_map = {81: "light.bedroom"}

    controller._handle_note_on(81)

    controller.backend.send_note.assert_called_once_with(81, "off")
    assert not controller.color_picker.active


def test_releasing_an_unavailable_pad_restores_its_colour(controller):
    controller.backend = MagicMock()
    controller.led_manager._unavailable_notes = {81}
    controller.button_map = {81: "light.bedroom"}

    controller._handle_note_on(81)
    controller.backend.send_note.reset_mock()
    controller._handle_note_off(81)

    controller.backend.send_note.assert_called_once_with(81, "gray_1")
