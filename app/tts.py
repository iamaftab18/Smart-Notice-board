import os
import shutil
import subprocess
import tempfile
import threading

_lock = threading.Lock()


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

    Returns (ok, error_message).
    """
    tts_binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not tts_binary:
        return False, "Text-to-speech is not installed on this device. Run: sudo apt install espeak-ng"

    player_binary = shutil.which("paplay") or shutil.which("aplay")

    with _lock:
        if player_binary:
            fd, wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                subprocess.run([tts_binary, "-w", wav_path, text], check=True, timeout=30)
                subprocess.run([player_binary, wav_path], check=True, timeout=120)
            except subprocess.CalledProcessError as exc:
                return False, f"Text-to-speech playback failed: {exc}"
            except subprocess.TimeoutExpired:
                return False, "Text-to-speech playback timed out."
            finally:
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
        else:
            # No dedicated player found -- fall back to espeak's own output.
            # Works, but may exhibit the "only once" issue described above.
            try:
                subprocess.run([tts_binary, text], check=True, timeout=120)
            except subprocess.CalledProcessError as exc:
                return False, f"Text-to-speech playback failed: {exc}"
            except subprocess.TimeoutExpired:
                return False, "Text-to-speech playback timed out."

    return True, None
