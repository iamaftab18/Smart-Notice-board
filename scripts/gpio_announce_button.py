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
import sys
import time
import urllib.request
from pathlib import Path


def _log(message):
    print(f"[button] {time.strftime('%H:%M:%S')} {message}", flush=True)


_log("script started, importing dependencies...")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.tts import speak  # noqa: E402

try:
    from gpiozero import Button
    from signal import pause
except Exception as exc:
    _log(f"FAILED to import gpiozero: {exc}")
    _log("Install it with: pip install -r requirements-gpio.txt "
         "(inside the project's venv, on the Pi).")
    sys.exit(1)

BOARD_API_URL = os.environ.get("NOTICE_BOARD_API_URL", "http://127.0.0.1:8000/api/notices/board")
BUTTON_PIN = int(os.environ.get("ANNOUNCE_BUTTON_PIN", 17))


def announce_published_notices():
    _log("PRESSED -- fetching published notices...")
    try:
        with urllib.request.urlopen(BOARD_API_URL, timeout=5) as response:
            data = json.load(response)
    except Exception as exc:
        _log(f"Could not reach notice board API at {BOARD_API_URL}: {exc}")
        speak("Could not reach the notice board.")
        return

    notices = data.get("notices", [])
    _log(f"found {len(notices)} published notice(s).")
    if not notices:
        speak("There are no published notices right now.")
        return

    for notice in notices:
        text = (
            f"{notice['title']}. "
            f"Date: {notice['notice_date_display']}. "
            f"{notice['description']}"
        )
        ok, error = speak(text)
        if not ok:
            _log(f"announcement failed: {error}")
        else:
            _log(f"announced notice #{notice['id']} OK.")


def main():
    _log(f"initializing GPIO{BUTTON_PIN} ...")
    try:
        button = Button(BUTTON_PIN, bounce_time=0.2)
    except Exception as exc:
        _log(f"FAILED to initialize GPIO{BUTTON_PIN}: {exc}")
        _log("Check the wiring (button leg -> GPIO17, other leg -> GND) and that this "
             "process has GPIO access (the 'pi' user is normally in the 'gpio' group already).")
        return

    button.when_pressed = announce_published_notices
    _log(f"ready. Listening for button presses on GPIO{BUTTON_PIN} (Ctrl+C to stop)...")
    pause()


if __name__ == "__main__":
    main()
