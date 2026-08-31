import os
import shutil
import subprocess
import tempfile
import threading
import time

_lock = threading.Lock()


def _log(message):
    print(f"[tts] {time.strftime('%H:%M:%S')} {message}", flush=True)


def is_available():
    return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None


def speak(text):
    """Speak text through the system's default audio output.

    Renders speech to a temporary WAV file with espeak(-ng), then hands
    playback to a dedicated player (paplay/aplay) instead of espeak's own
    audio output. espeak's built-in playback can work once and then go
    silent on every later call against the same sink -- especially a
    Bluetooth one -- until the process is restarted, because it doesn't
    reliably release the device. A dedicated player opens and closes the
    device fresh on every call, which avoids that.

    Every step is logged to stdout (visible in the terminal, or via
    `journalctl` if running as a systemd service) so a failure shows
    exactly which stage broke and why, instead of just "no sound".

    Returns (ok, error_message).
    """
    tts_binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not tts_binary:
        _log("FAILED: espeak-ng/espeak not found on PATH.")
        return False, "Text-to-speech is not installed on this device. Run: sudo apt install espeak-ng"

    player_binary = shutil.which("paplay") or shutil.which("aplay")
    _log(f"engine={tts_binary} player={player_binary or '(none -- using espeak built-in output)'}")

    with _lock:
        if player_binary:
            fd, wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                _log(f"rendering speech to {wav_path} ...")
                render = subprocess.run(
                    [tts_binary, "-w", wav_path, text],
                    capture_output=True, text=True, timeout=30,
                )
                if render.returncode != 0:
                    err = render.stderr.strip() or "unknown error"
                    _log(f"FAILED: espeak render exited {render.returncode}: {err}")
                    return False, f"Speech rendering failed: {err}"

                size = os.path.getsize(wav_path) if os.path.exists(wav_path) else 0
                if size == 0:
                    _log("FAILED: rendered WAV file is empty.")
                    return False, "Speech rendering produced an empty audio file."
                _log(f"rendered {size} bytes, playing via {player_binary} ...")

                play = subprocess.run(
                    [player_binary, wav_path],
                    capture_output=True, text=True, timeout=120,
                )
                if play.returncode != 0:
                    err = play.stderr.strip() or "unknown error"
                    _log(f"FAILED: {player_binary} exited {play.returncode}: {err}")
                    return False, f"Audio playback failed: {err}"

                _log("playback finished OK.")
            except subprocess.TimeoutExpired as exc:
                _log(f"FAILED: timed out ({exc}).")
                return False, "Text-to-speech timed out."
            finally:
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
        else:
            try:
                _log("no dedicated player found; using espeak's built-in output "
                     "(known to go silent after the first call -- install pulseaudio-utils or alsa-utils).")
                result = subprocess.run([tts_binary, text], capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    err = result.stderr.strip() or "unknown error"
                    _log(f"FAILED: espeak exited {result.returncode}: {err}")
                    return False, f"Text-to-speech failed: {err}"
                _log("playback finished OK (espeak built-in output).")
            except subprocess.TimeoutExpired:
                _log("FAILED: timed out.")
                return False, "Text-to-speech timed out."

    return True, None
