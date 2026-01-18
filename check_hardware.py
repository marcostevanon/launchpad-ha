#!/usr/bin/env python3
"""
Simple script to check Launchpad hardware connection and LED functionality.
"""
import time
import sys
import os

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ha_launchpad.infrastructure.midi.mido_backend import MidoBackend

def main():
    print("Checking for Launchpad...")
    backend = MidoBackend()
    
    if not backend.find_and_open():
        print("❌ Launchpad not found!")
        print("Please check USB connection and ensure no other software is using the device.")
        sys.exit(1)
        
    print("✅ Launchpad found and ports opened.")
    
    try:
        print("\nLighting up some LEDs...")
        # Cycle through some colors
        colors = ["red_1", "green_1", "blue_1", "yellow_1", "pink_1", "cyan_1", "white", "off"]
        
        # Light up grid
        for i, color in enumerate(colors):
            print(f"Color: {color}")
            # Light up a row
            row = 8 - i
            start_note = row * 10 + 1
            for note in range(start_note, start_note + 9):
                 backend.send_note(note, color)
            time.sleep(0.5)
            
        print("\nLED Test complete.")
        print("Please press buttons on the Launchpad. Press Ctrl+C to exit.")
        print("-" * 50)
        
        midi_in = backend.iter_incoming()
        if not midi_in:
             print("❌ MIDI input not available.")
             sys.exit(1)
             
        while True:
            for msg in midi_in.iter_pending():
                 print(f"Received: {msg}")
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # turn off
        for note in range(128):
            backend.send_note(note, "off")
        backend.close()
        print("Backend closed.")

if __name__ == "__main__":
    main()
