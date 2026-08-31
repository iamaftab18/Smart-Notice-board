#!/usr/bin/env python3
"""Physical push-button announcer for the Smart Notice Board.

Wire a push button between GPIO17 (physical pin 11) and GND (physical pin
9) -- gpiozero's internal pull-up means no external resistor is needed.

On each press, this fetches whatever notices are currently published from
the running Flask app's JSON API and reads them aloud (title, date,
description) through the system's default audio device, e.g. a paired
Bluetooth speaker.

Runs as its own process alongside the Flask app -- see README.md for the
systemd service that keeps it running on boot.
"""
import json
import os
import shutil
import subprocess
import urllib.request

from gpiozero import Button
from signal import pause

BOARD_API_URL = os.environ.get("NOTICE_BOARD_API_URL", "http://127.0.0.1:8000/api/notices/board")
BUTTON_PIN = int(os.environ.get("ANNOUNCE_BUTTON_PIN", 17))


def speak(text):
    tts_binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not tts_binary:
        print("espeak-ng is not installed; run: sudo apt install espeak-ng")
        return
    subprocess.run([tts_binary, text], check=False)


def announce_published_notices():
    try:
        with urllib.request.urlopen(BOARD_API_URL, timeout=5) as response:
            data = json.load(response)
    except Exception as exc:
        print(f"Could not reach notice board API at {BOARD_API_URL}: {exc}")
        speak("Could not reach the notice board.")
        return

    notices = data.get("notices", [])
    if not notices:
        speak("There are no published notices right now.")
        return

    for notice in notices:
        text = (
            f"{notice['title']}. "
            f"Date: {notice['notice_date_display']}. "
            f"{notice['description']}"
        )
        speak(text)


def main():
    button = Button(BUTTON_PIN, bounce_time=0.2)
    button.when_pressed = announce_published_notices
    print(f"Listening for button presses on GPIO{BUTTON_PIN} (Ctrl+C to stop)...")
    pause()


if __name__ == "__main__":
    main()
