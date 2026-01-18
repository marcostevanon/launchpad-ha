"""MIDI backend using mido + python-rtmidi (RtMidi) for Launchpad access."""

import usb.core
from typing import Optional
import logging
import mido

from src.ha_launchpad.config.settings import (
    LAUNCHPAD_IDENT,
    LAUNCHPAD_VENDOR,
    LAUNCHPAD_PRODUCT,
)
from src.ha_launchpad.config.mapping import COLORS
from .interface import MidiBackend

logger = logging.getLogger(__name__)


class MidoBackend(MidiBackend):
    def __init__(self, ident: Optional[str] = None):
        self.usb_device = None
        self.ident = ident or LAUNCHPAD_IDENT
        self.midi_in = None
        self.midi_out = None

    def find_and_open(self) -> bool:
        """Search for the Launchpad MIDI ports and open them."""

        self.usb_device = usb.core.find(
            idVendor=LAUNCHPAD_VENDOR, idProduct=LAUNCHPAD_PRODUCT
        )

        input_ports = mido.get_input_names()  # pyright: ignore
        output_ports = mido.get_output_names()  # pyright: ignore
        logger.debug("Available MIDI input ports: %s", input_ports)
        logger.debug("Available MIDI output ports: %s", output_ports)

        launchpad_in = None
        launchpad_out = None
        for port in input_ports:
            if self.ident in port:
                launchpad_in = port
                break
        for port in output_ports:
            if self.ident in port:
                launchpad_out = port
                break

        if launchpad_in and launchpad_out:
            logger.info(
                "Opening Launchpad ports: in=%s out=%s", launchpad_in, launchpad_out
            )
            self.midi_in = mido.open_input(launchpad_in)  # pyright: ignore
            self.midi_out = mido.open_output(launchpad_out)  # pyright: ignore

            # Enter Programmer Mode (best-effort)
            PROGRAMMER_MODE = [0x00, 0x20, 0x29, 0x02, 0x0D, 0x0E, 0x01]
            try:
                self.midi_out.send(mido.Message("sysex", data=PROGRAMMER_MODE))
            except Exception as exc:
                logger.warning("Failed to send programmer mode SysEx: %s", exc)

            return True

        logger.warning("Launchpad ports with ident '%s' not found", self.ident)
        return False

    def send_note(self, note: int, color: str, channel: int = 0):
        if not self.midi_out:
            logger.debug("send_note: output not open (note=%s color=%s)", note, color)
            return
        try:
            velocity = COLORS.get(color, 0)
            msg = mido.Message("note_on", note=note, velocity=velocity, channel=channel)
            self.midi_out.send(msg)
            logger.debug("Sent note (off)=%s channel=%s", note, channel)
        except Exception as exc:
            logger.warning("Failed to send note=%s: %s", note, exc)

    def iter_incoming(self):
        # Return the input object which supports iteration over incoming messages.
        return self.midi_in

    def is_connected(self) -> bool:
        """Check if the USB device is still available."""
        self.usb_device = usb.core.find(
            idVendor=LAUNCHPAD_VENDOR, idProduct=LAUNCHPAD_PRODUCT
        )
        return self.usb_device is not None

    def close(self):
        try:
            if self.midi_in:
                self.midi_in.close()
                logger.info("Closed MIDI input")
        except Exception as exc:
            logger.debug("Error closing MIDI input: %s", exc)
        try:
            if self.midi_out:
                self.midi_out.close()
                logger.info("Closed MIDI output")
        except Exception as exc:
            logger.debug("Error closing MIDI output: %s", exc)
