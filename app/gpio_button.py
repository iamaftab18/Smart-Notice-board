import os
import threading
import time

from sqlalchemy import case

from app.models import Notice
from app.tts import speak

BUTTON_PIN = int(os.environ.get("ANNOUNCE_BUTTON_PIN", 17))
DEBOUNCE_MS = 300
HEARTBEAT_SECONDS = 30

_PRIORITY_RANK = case(
    (Notice.priority == "urgent", 3),
    (Notice.priority == "important", 2),
    else_=1,
)


def _log(message):
    print(f"[button] {time.strftime('%H:%M:%S')} {message}", flush=True)


def _announce_published_notices(app):
    _log("PRESSED -- fetching published notices...")
    with app.app_context():
        notices = (
            Notice.query.filter_by(is_published=True)
            .order_by(_PRIORITY_RANK.desc(), Notice.notice_date.desc(), Notice.updated_at.desc())
            .all()
        )
        notice_dicts = [n.to_dict() for n in notices]

    _log(f"found {len(notice_dicts)} published notice(s).")
    if not notice_dicts:
        speak("There are no published notices right now.")
        return

    for notice in notice_dicts:
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


def start_button_listener(app):
    """Start listening for the physical announce button in a background thread
    of the main application process, so `python3 run.py` alone is enough --
    no separate script needs to be run alongside it.

    Safe to call even where RPi.GPIO / the button hardware isn't present:
    logs a message and does nothing in that case, so it never breaks running
    the app on a dev machine without GPIO. Set DISABLE_GPIO_BUTTON=1 to skip
    it deliberately (e.g. when running multiple gunicorn workers, where each
    worker would otherwise register its own listener on the same pin and
    every press would announce multiple times -- use the standalone
    scripts/gpio_announce_button.py as a single dedicated process instead).
    """
    if os.environ.get("DISABLE_GPIO_BUTTON") == "1":
        _log("disabled via DISABLE_GPIO_BUTTON=1, skipping.")
        return

    try:
        import RPi.GPIO as GPIO
    except Exception as exc:
        _log(f"RPi.GPIO not available ({exc}); physical announce button disabled "
             f"for this process. Install with: pip install -r requirements-gpio.txt")
        return

    def _worker():
        _log(f"initializing GPIO{BUTTON_PIN} using RPi.GPIO ...")
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                BUTTON_PIN, GPIO.FALLING,
                callback=lambda channel: _announce_published_notices(app),
                bouncetime=DEBOUNCE_MS,
            )
        except Exception as exc:
            _log(f"FAILED to initialize GPIO{BUTTON_PIN}: {exc}")
            _log("Check the wiring (button leg -> GPIO17, other leg -> GND) and that "
                 "this process has GPIO access.")
            return

        _log(f"ready. Listening for button presses on GPIO{BUTTON_PIN}.")
        last_heartbeat = time.time()
        while True:
            time.sleep(1)
            if time.time() - last_heartbeat >= HEARTBEAT_SECONDS:
                _log("still alive, waiting for button presses...")
                last_heartbeat = time.time()

    threading.Thread(target=_worker, daemon=True, name="gpio-button-listener").start()
